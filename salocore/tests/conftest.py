import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from salocore.models import User

# ─────────────────────────── Fixtures ────────────────────────────


@pytest.fixture
def api_client():
    """Чистий DRF-клієнт без авторизації."""
    return APIClient()


@pytest.fixture
def user(db):
    """Звичайний користувач у БД."""
    return User.objects.create_user(
        username="testuser",
        email="testuser@mail.com",
        password="TestPass123!",
    )


@pytest.fixture
def auth_client(api_client, user):
    """DRF-клієнт, авторизований як user, + його refresh-токен."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client, str(refresh)
