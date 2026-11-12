import pytest

from tests.factories import OrganizationFactory, VendorFactory

pytestmark = pytest.mark.django_db

VENDOR = {"name": "Acme Supplies", "gstin": "29AABCU9603R1ZX"}


def test_finance_admin_creates_vendor_and_state_code_is_taken_from_gstin(client_for, finance_admin):
    response = client_for(finance_admin).post("/api/vendors/", VENDOR, format="json")

    assert response.status_code == 201
    assert response.json()["state_code"] == "29"


def test_submitter_cannot_create_vendor(client_for, submitter):
    response = client_for(submitter).post("/api/vendors/", VENDOR, format="json")

    assert response.status_code == 403


def test_bad_gstin_is_rejected_by_api(client_for, finance_admin):
    response = client_for(finance_admin).post(
        "/api/vendors/", {"name": "Bad", "gstin": "NOTAGSTIN"}, format="json"
    )

    assert response.status_code == 400
    assert "gstin" in response.json()


def test_duplicate_gstin_in_same_org_is_rejected(client_for, finance_admin):
    VendorFactory(organization=finance_admin.organization, gstin=VENDOR["gstin"])

    response = client_for(finance_admin).post("/api/vendors/", VENDOR, format="json")

    assert response.status_code == 400


def test_same_gstin_is_allowed_in_another_org(client_for, finance_admin):
    VendorFactory(organization=OrganizationFactory(), gstin=VENDOR["gstin"])

    response = client_for(finance_admin).post("/api/vendors/", VENDOR, format="json")

    assert response.status_code == 201


def test_search_by_name(client_for, submitter):
    VendorFactory(organization=submitter.organization, name="Sharma Traders")
    VendorFactory(organization=submitter.organization, name="Gupta Metals")

    response = client_for(submitter).get("/api/vendors/?search=sharma")

    assert [v["name"] for v in response.json()["results"]] == ["Sharma Traders"]


def test_vendor_update_and_delete(client_for, finance_admin):
    vendor = VendorFactory(organization=finance_admin.organization)
    client = client_for(finance_admin)

    assert (
        client.patch(f"/api/vendors/{vendor.id}/", {"name": "Renamed"}, format="json").status_code
        == 200
    )
    assert client.delete(f"/api/vendors/{vendor.id}/").status_code == 204
