from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.invoices.models import Invoice
from tests.factories import InvoiceFactory, VendorFactory

pytestmark = pytest.mark.django_db


def payload(vendor, **overrides):
    data = {
        "vendor": vendor.id,
        "invoice_no": "INV-1001",
        "invoice_date": "2026-10-05",
        "taxable_value": "1000.00",
        "cgst": "90.00",
        "sgst": "90.00",
        "igst": "0.00",
        "total": "1180.00",
    }
    data.update(overrides)
    return data


@pytest.fixture
def vendor(org):
    return VendorFactory(organization=org, state="29")


def test_create_intra_state_invoice(client_for, submitter, vendor):
    response = client_for(submitter).post("/api/invoices/", payload(vendor), format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["created_by"] == submitter.id
    assert Invoice.objects.get(pk=body["id"]).organization == submitter.organization


def test_create_inter_state_invoice(client_for, submitter, org):
    other_state_vendor = VendorFactory(organization=org, state="27")
    data = payload(other_state_vendor, cgst="0", sgst="0", igst="180.00")

    response = client_for(submitter).post("/api/invoices/", data, format="json")

    assert response.status_code == 201


def test_api_rejects_igst_on_intra_state_invoice(client_for, submitter, vendor):
    data = payload(vendor, cgst="0", sgst="0", igst="180.00")

    response = client_for(submitter).post("/api/invoices/", data, format="json")

    assert response.status_code == 400
    assert "igst" in response.json()


def test_api_rejects_wrong_total(client_for, submitter, vendor):
    response = client_for(submitter).post(
        "/api/invoices/", payload(vendor, total="1000.00"), format="json"
    )

    assert response.status_code == 400
    assert "total" in response.json()


def test_duplicate_invoice_no_for_same_vendor_is_rejected(client_for, submitter, vendor):
    client = client_for(submitter)
    assert client.post("/api/invoices/", payload(vendor), format="json").status_code == 201

    response = client.post("/api/invoices/", payload(vendor), format="json")

    assert response.status_code == 400
    assert "invoice_no" in response.json()


def test_same_invoice_no_is_fine_for_another_vendor(client_for, submitter, vendor, org):
    client = client_for(submitter)
    client.post("/api/invoices/", payload(vendor), format="json")
    second_vendor = VendorFactory(organization=org)

    response = client.post("/api/invoices/", payload(second_vendor), format="json")

    assert response.status_code == 201


def test_filter_by_status_vendor_and_date_range(client_for, submitter, vendor, org):
    other_vendor = VendorFactory(organization=org)
    InvoiceFactory(created_by=submitter, vendor=vendor, invoice_date=date(2026, 9, 1))
    wanted = InvoiceFactory(
        created_by=submitter, vendor=vendor, invoice_date=date(2026, 10, 10), status="submitted"
    )
    InvoiceFactory(created_by=submitter, vendor=other_vendor, invoice_date=date(2026, 10, 12))
    client = client_for(submitter)

    def ids(query):
        return [i["id"] for i in client.get(f"/api/invoices/?{query}").json()["results"]]

    assert ids("status=submitted") == [wanted.id]
    assert ids(f"vendor={vendor.id}&date_from=2026-10-01&date_to=2026-10-31") == [wanted.id]
    assert len(ids("date_from=2026-10-01")) == 2


def test_search_by_invoice_no_and_vendor_name(client_for, submitter, org):
    sharma = VendorFactory(organization=org, name="Sharma Traders")
    target = InvoiceFactory(created_by=submitter, vendor=sharma, invoice_no="SH-77")
    InvoiceFactory(created_by=submitter)
    client = client_for(submitter)

    by_number = client.get("/api/invoices/?search=SH-77").json()["results"]
    by_vendor = client.get("/api/invoices/?search=sharma").json()["results"]

    assert [i["id"] for i in by_number] == [target.id]
    assert [i["id"] for i in by_vendor] == [target.id]


def test_list_is_paginated(client_for, submitter):
    InvoiceFactory.create_batch(25, created_by=submitter)

    first = client_for(submitter).get("/api/invoices/").json()
    second = client_for(submitter).get("/api/invoices/?page=2").json()

    assert first["count"] == 25
    assert len(first["results"]) == 20
    assert len(second["results"]) == 5


def test_invoice_list_query_count_does_not_grow_with_rows(
    client_for, submitter, django_assert_num_queries
):
    InvoiceFactory.create_batch(15, created_by=submitter)

    with django_assert_num_queries(2):
        response = client_for(submitter).get("/api/invoices/")

    assert len(response.json()["results"]) == 15


def test_draft_invoice_can_be_edited_and_deleted_by_creator(client_for, submitter):
    invoice = InvoiceFactory(created_by=submitter)
    client = client_for(submitter)

    edit = client.patch(f"/api/invoices/{invoice.id}/", {"invoice_no": "INV-NEW"}, format="json")
    delete = client.delete(f"/api/invoices/{invoice.id}/")

    assert edit.status_code == 200
    assert delete.status_code == 204


def test_other_user_cannot_edit_someone_elses_invoice(client_for, submitter, org):
    invoice = InvoiceFactory(created_by=submitter)
    colleague = type(submitter).objects.create_user(
        username="colleague", password="x", organization=org
    )

    response = client_for(colleague).patch(
        f"/api/invoices/{invoice.id}/", {"invoice_no": "X"}, format="json"
    )

    assert response.status_code == 403


def test_paid_invoice_cannot_be_edited_or_deleted(client_for, finance_admin):
    invoice = InvoiceFactory(created_by=finance_admin, status=Invoice.Status.PAID)
    client = client_for(finance_admin)

    edit = client.patch(f"/api/invoices/{invoice.id}/", {"invoice_no": "NEW"}, format="json")
    delete = client.delete(f"/api/invoices/{invoice.id}/")

    assert edit.status_code == 409
    assert delete.status_code == 409
    invoice.refresh_from_db()
    assert invoice.invoice_no != "NEW"


def test_paid_invoice_cannot_be_saved_through_the_model(finance_admin):
    invoice = InvoiceFactory(created_by=finance_admin, status=Invoice.Status.PAID)
    invoice.invoice_no = "CHANGED"

    with pytest.raises(ValidationError):
        invoice.save()


def test_submitted_invoice_is_locked_for_editing(client_for, submitter):
    invoice = InvoiceFactory(created_by=submitter, status=Invoice.Status.SUBMITTED)

    response = client_for(submitter).patch(
        f"/api/invoices/{invoice.id}/", {"invoice_no": "NEW"}, format="json"
    )

    assert response.status_code == 409
