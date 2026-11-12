import pytest

from tests.factories import InvoiceFactory, OrganizationFactory, UserFactory, VendorFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def other_org_user():
    return UserFactory(organization=OrganizationFactory())


def test_invoice_list_only_shows_own_organization(client_for, submitter, other_org_user):
    mine = InvoiceFactory(created_by=submitter)
    InvoiceFactory(created_by=other_org_user)

    results = client_for(submitter).get("/api/invoices/").json()["results"]

    assert [i["id"] for i in results] == [mine.id]


def test_other_organizations_invoice_is_not_found(client_for, submitter, other_org_user):
    foreign = InvoiceFactory(created_by=other_org_user)

    assert client_for(submitter).get(f"/api/invoices/{foreign.id}/").status_code == 404


def test_other_organizations_invoice_cannot_be_changed(client_for, finance_admin, other_org_user):
    foreign = InvoiceFactory(created_by=other_org_user)
    client = client_for(finance_admin)

    assert (
        client.patch(f"/api/invoices/{foreign.id}/", {"invoice_no": "X"}, format="json").status_code
        == 404
    )
    assert client.delete(f"/api/invoices/{foreign.id}/").status_code == 404


def test_vendor_list_only_shows_own_organization(client_for, submitter, other_org_user):
    mine = VendorFactory(organization=submitter.organization)
    VendorFactory(organization=other_org_user.organization)

    results = client_for(submitter).get("/api/vendors/").json()["results"]

    assert [v["id"] for v in results] == [mine.id]


def test_invoice_cannot_use_a_vendor_of_another_organization(client_for, submitter, other_org_user):
    foreign_vendor = VendorFactory(organization=other_org_user.organization)
    data = {
        "vendor": foreign_vendor.id,
        "invoice_no": "INV-1",
        "invoice_date": "2026-10-05",
        "taxable_value": "1000.00",
        "cgst": "90.00",
        "sgst": "90.00",
        "total": "1180.00",
    }

    response = client_for(submitter).post("/api/invoices/", data, format="json")

    assert response.status_code == 400
    assert "vendor" in response.json()
