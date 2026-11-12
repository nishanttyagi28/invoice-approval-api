import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_swagger_ui_is_served():
    assert APIClient().get("/api/docs/").status_code == 200


def test_schema_lists_the_main_endpoints():
    response = APIClient().get("/api/schema/?format=json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in [
        "/api/auth/token/",
        "/api/invoices/",
        "/api/invoices/{id}/approve/",
        "/api/invoices/{id}/audit/",
        "/api/reports/summary/",
    ]:
        assert path in paths
