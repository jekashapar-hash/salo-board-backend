"""
Тести для аутентифікації:
  - POST /api/register
  - POST /api/login
  - POST /api/logout
  - POST /api/token/refresh
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from salocore.models import User

# ─────────────────────────── Fixtures ────────────────────────────


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="authuser",
        email="authuser@mail.com",
        password="TestPass123!",
    )


@pytest.fixture
def auth_client(api_client, user):
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client, str(refresh)


# ─────────────────────────── Register ────────────────────────────


@pytest.mark.django_db
class TestRegister:
    url = reverse("register")

    def test_success(self, api_client):
        """Реєстрація з валідними даними → 201 + access і refresh токени."""
        response = api_client.post(
            self.url,
            {"email": "newuser@mail.com", "password": "SecurePass1!"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "refresh" in response.data

    def test_user_is_saved_to_db(self, api_client):
        """Після реєстрації юзер має бути в БД."""
        api_client.post(self.url, {"email": "saved@mail.com", "password": "Pass123!"})

        assert User.objects.filter(email="saved@mail.com").exists()

    def test_user_profile_auto_created(self, api_client):
        """UserProfile повинен автоматично створитися через сигнал."""
        api_client.post(self.url, {"email": "profile@mail.com", "password": "Pass123!"})

        user = User.objects.get(email="profile@mail.com")
        assert hasattr(user, "userprofile")

    def test_duplicate_email(self, api_client, user):
        """Реєстрація з вже існуючим email → 400."""
        response = api_client.post(
            self.url,
            {"email": user.email, "password": "AnotherPass1!"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_missing_email(self, api_client):
        """Реєстрація без email → 400."""
        response = api_client.post(self.url, {"password": "Pass123!"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_password(self, api_client):
        """Реєстрація без password → 400."""
        response = api_client.post(self.url, {"email": "nopass@mail.com"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invite_code_generated(self, api_client):
        """У нового юзера повинен бути invite_code."""
        api_client.post(self.url, {"email": "invite@mail.com", "password": "Pass123!"})

        user = User.objects.get(email="invite@mail.com")
        assert user.invite_code is not None
        assert len(user.invite_code) == 8


# ─────────────────────────── Login ────────────────────────────────


@pytest.mark.django_db
class TestLogin:
    url = reverse("login")

    def test_success(self, api_client, user):
        """Логін з правильними кредами → 200 + токени."""
        response = api_client.post(
            self.url,
            {"email": user.email, "password": "TestPass123!"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_wrong_password(self, api_client, user):
        """Невірний пароль → 401."""
        response = api_client.post(
            self.url,
            {"email": user.email, "password": "WrongPassword!"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_nonexistent_email(self, api_client):
        """Email якого немає в БД → 401."""
        response = api_client.post(
            self.url,
            {"email": "ghost@mail.com", "password": "Pass123!"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_email(self, api_client):
        """Пустий email → 400."""
        response = api_client.post(self.url, {"password": "Pass123!"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_password(self, api_client, user):
        """Пустий password → 400."""
        response = api_client.post(self.url, {"email": user.email})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────── Logout ───────────────────────────────


@pytest.mark.django_db
class TestLogout:
    url = reverse("logout")

    def test_success(self, auth_client):
        """Logout з валідним refresh-токеном → 200."""
        client, refresh_token = auth_client
        response = client.post(self.url, {"refresh": refresh_token})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Вихід успішний"

    def test_token_blacklisted_after_logout(self, auth_client):
        """Після logout той самий refresh-токен більше не працює."""
        client, refresh_token = auth_client
        client.post(self.url, {"refresh": refresh_token})

        # Спробуємо використати той самий токен знову
        response = client.post(self.url, {"refresh": refresh_token})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_refresh_token(self, auth_client):
        """Logout без refresh-токена → 400."""
        client, _ = auth_client
        response = client.post(self.url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_invalid_refresh_token(self, auth_client):
        """Logout з невалідним токеном → 400."""
        client, _ = auth_client
        response = client.post(self.url, {"refresh": "this.is.not.valid"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated(self, api_client):
        """Logout без JWT в заголовку → 401."""
        response = api_client.post(self.url, {"refresh": "some_token"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────────────── Token Refresh ────────────────────────


@pytest.mark.django_db
class TestTokenRefresh:
    url = reverse("token_refresh")

    def test_success(self, auth_client):
        """Оновлення токена з валідним refresh → 200 + новий access."""
        _, refresh_token = auth_client
        api_client = APIClient()
        response = api_client.post(self.url, {"refresh": refresh_token})

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_invalid_token(self, api_client):
        """Невалідний refresh-токен → 401."""
        response = api_client.post(self.url, {"refresh": "invalid.token.here"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_token(self, api_client):
        """Запит без refresh-поля → 400."""
        response = api_client.post(self.url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
