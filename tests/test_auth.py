import pytest
from rest_framework.test import APIClient

from tests.factories import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


def test_token_and_refresh_flow():
    user = UserFactory()
    client = APIClient()

    response = client.post(
        "/api/auth/token/", {"username": user.username, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    tokens = response.json()

    refreshed = client.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert refreshed.status_code == 200
    assert "access" in refreshed.json()


def test_access_token_opens_protected_endpoint():
    user = UserFactory()
    client = APIClient()
    tokens = client.post(
        "/api/auth/token/", {"username": user.username, "password": PASSWORD}, format="json"
    ).json()

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get("/api/invoices/").status_code == 200


def test_wrong_password_is_rejected():
    user = UserFactory()
    response = APIClient().post(
        "/api/auth/token/", {"username": user.username, "password": "nope"}, format="json"
    )
    assert response.status_code == 401


def test_protected_endpoint_needs_token():
    assert APIClient().get("/api/invoices/").status_code == 401


def test_token_endpoint_is_throttled():
    client = APIClient()
    statuses = [
        client.post(
            "/api/auth/token/", {"username": "x", "password": "y"}, format="json"
        ).status_code
        for _ in range(11)
    ]
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
