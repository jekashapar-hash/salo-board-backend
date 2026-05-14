import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from salocore.models import User, UserTelegramProfile


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="tguser", email="tg@mail.com", password="TestPass123!")


@pytest.fixture
def auth_client(api_client, user):
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.mark.django_db
class TestUserTelegramStatus:
    url = reverse("user-telegram-status")

    def test_status_false_initially(self, auth_client):
        """Користувач спочатку не має підключеного Telegram."""
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["connected"] is False

    def test_status_true_after_profile_created(self, auth_client, user):
        """Користувач має підключений Telegram після створення профілю."""
        UserTelegramProfile.objects.create(user=user, chat_id=123456789)

        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["connected"] is True

    def test_unauthenticated_returns_401(self, api_client):
        """Неавторизований запит повертає 401."""
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
