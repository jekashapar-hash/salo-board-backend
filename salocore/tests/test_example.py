import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
def test_user_view_unauthorized(client):
    """
    Sample test to verify testing infrastructure.
    Checks that unauthorized user cannot access user profile list.
    """
    url = reverse("user-profile") # Based on salocore/urls.py
    response = client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
