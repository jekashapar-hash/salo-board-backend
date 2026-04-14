"""
Тести для профілю користувача:
  - GET  /api/user        → UserProfileView
  - PATCH /api/user       → UserProfileView
  - GET  /api/user/name   → UserNameView
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
    u = User.objects.create_user(
        username="profileuser",
        email="profile@mail.com",
        password="TestPass123!",
        first_name="Іван",
        last_name="Богун",
    )
    return u


@pytest.fixture
def auth_client(api_client, user):
    """Авторизований клієнт від імені user."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


# ─────────────────────────── GET /api/user ───────────────────────


@pytest.mark.django_db
class TestGetUserProfile:
    url = reverse("user-profile")

    def test_returns_200_when_authenticated(self, auth_client):
        """Авторизований юзер отримує свій профіль → 200."""
        response = auth_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_when_unauthenticated(self, api_client):
        """Неавторизований юзер → 401."""
        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_response_contains_email(self, auth_client, user):
        """Відповідь містить email поточного юзера."""
        response = auth_client.get(self.url)

        # API повертає camelCase через djangorestframework-camel-case
        assert response.data["email"] == user.email

    def test_response_contains_name_fields(self, auth_client, user):
        """Відповідь містить firstName і lastName."""
        response = auth_client.get(self.url)

        assert response.data["firstName"] == user.first_name
        assert response.data["lastName"] == user.last_name

    def test_response_contains_date_joined(self, auth_client):
        """Відповідь містить dateJoined."""
        response = auth_client.get(self.url)

        assert "dateJoined" in response.data

    def test_response_contains_profile_fields(self, auth_client):
        """Відповідь містить поля профілю: city, organization, telegram, discord."""
        response = auth_client.get(self.url)

        for field in ("city", "organization", "telegram", "discord"):
            assert field in response.data

    def test_cannot_see_another_users_profile(self, db, api_client):
        """Кожен юзер бачить лише свій профіль (перевірка ізоляції)."""
        other_user = User.objects.create_user(
            username="other",
            email="other@mail.com",
            password="Pass123!",
        )
        refresh = RefreshToken.for_user(other_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "other@mail.com"


# ─────────────────────────── PATCH /api/user ─────────────────────


@pytest.mark.django_db
class TestPatchUserProfile:
    url = reverse("user-profile")

    def test_update_first_name(self, auth_client, user):
        """PATCH з firstName → ім'я оновлюється."""
        response = auth_client.patch(self.url, {"first_name": "Петро"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["firstName"] == "Петро"

        user.refresh_from_db()
        assert user.first_name == "Петро"

    def test_update_last_name(self, auth_client, user):
        """PATCH з lastName → прізвище оновлюється."""
        response = auth_client.patch(self.url, {"last_name": "Сагайдачний"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["lastName"] == "Сагайдачний"

    def test_update_city(self, auth_client, user):
        """PATCH з city → поле профілю оновлюється в UserProfile."""
        response = auth_client.patch(self.url, {"city": "Київ"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["city"] == "Київ"

        user.userprofile.refresh_from_db()
        assert user.userprofile.city == "Київ"

    def test_update_telegram(self, auth_client, user):
        """PATCH з telegram → оновлюється в UserProfile."""
        response = auth_client.patch(self.url, {"telegram": "@myhandle"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["telegram"] == "@myhandle"

    def test_update_multiple_fields_at_once(self, auth_client, user):
        """PATCH кількох полів одразу."""
        response = auth_client.patch(
            self.url,
            {
                "first_name": "Микола",
                "city": "Львів",
                "organization": "KPI",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["firstName"] == "Микола"
        assert response.data["city"] == "Львів"
        assert response.data["organization"] == "KPI"

    def test_partial_update_does_not_erase_existing_data(self, auth_client, user):
        """PATCH одного поля не затирає інші."""
        # Спочатку встановимо ім'я
        auth_client.patch(self.url, {"first_name": "Тарас"})

        # Оновимо тільки місто
        auth_client.patch(self.url, {"city": "Харків"})

        # Ім'я повинно залишитись
        response = auth_client.get(self.url)
        assert response.data["firstName"] == "Тарас"
        assert response.data["city"] == "Харків"

    def test_unauthenticated_cannot_patch(self, api_client):
        """PATCH без авторизації → 401."""
        response = api_client.patch(self.url, {"first_name": "Хакер"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cannot_update_email_via_patch(self, auth_client, user):
        """email — read-only поле, змінити через PATCH не можна."""
        auth_client.patch(self.url, {"email": "hacked@mail.com"})

        user.refresh_from_db()
        assert user.email == "profile@mail.com"  # не змінився


# ─────────────────────────── GET /api/user/name ──────────────────


@pytest.mark.django_db
class TestGetUserName:
    url = reverse("user-name")

    def test_returns_200_when_authenticated(self, auth_client):
        """Авторизований юзер → 200."""
        response = auth_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_when_unauthenticated(self, api_client):
        """Без токена → 401."""
        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_only_name_fields(self, auth_client, user):
        """Відповідь містить лише firstName і lastName."""
        response = auth_client.get(self.url)

        assert set(response.data.keys()) == {"firstName", "lastName"}

    def test_correct_values_returned(self, auth_client, user):
        """Значення firstName і lastName відповідають тим, що в БД."""
        response = auth_client.get(self.url)

        assert response.data["firstName"] == user.first_name
        assert response.data["lastName"] == user.last_name

    def test_empty_name_when_not_set(self, db, api_client):
        """Якщо ім'я не задане → порожні рядки."""
        user_no_name = User.objects.create_user(
            username="noname",
            email="noname@mail.com",
            password="Pass123!",
        )
        refresh = RefreshToken.for_user(user_no_name)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["firstName"] == ""
        assert response.data["lastName"] == ""
