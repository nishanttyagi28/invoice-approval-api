import pytest
from django.core.management import call_command

from apps.accounts.models import Organization
from apps.approvals.models import AuditLog
from apps.invoices.models import Invoice
from apps.invoices.tax import is_intra_state, validate_amounts
from apps.vendors.models import Vendor

pytestmark = pytest.mark.django_db


def test_seed_creates_demo_vendors_and_invoices_in_every_status():
    call_command("seed_demo")

    assert Vendor.objects.count() == 3
    assert Invoice.objects.count() == 8
    statuses = set(Invoice.objects.values_list("status", flat=True))
    assert statuses == {"draft", "submitted", "reviewed", "approved", "rejected", "paid"}


def test_seeded_data_is_marked_as_demo():
    call_command("seed_demo")

    assert "demo data" in Organization.objects.get().name
    assert all(name.startswith("DEMO ") for name in Vendor.objects.values_list("name", flat=True))
    assert all(
        no.startswith("DEMO-") for no in Invoice.objects.values_list("invoice_no", flat=True)
    )


def test_seeded_invoices_follow_the_gst_rules():
    call_command("seed_demo")

    for invoice in Invoice.objects.select_related("vendor", "organization"):
        validate_amounts(
            intra_state=is_intra_state(invoice.vendor, invoice.organization),
            taxable_value=invoice.taxable_value,
            cgst=invoice.cgst,
            sgst=invoice.sgst,
            igst=invoice.igst,
            total=invoice.total,
        )


def test_seeded_invoices_went_through_the_audit_log():
    call_command("seed_demo")

    paid = Invoice.objects.get(invoice_no="DEMO-002")
    steps = list(AuditLog.objects.filter(invoice=paid).values_list("to_status", flat=True))

    assert steps == ["submitted", "reviewed", "approved", "paid"]


def test_running_seed_twice_does_not_duplicate_data():
    call_command("seed_demo")
    call_command("seed_demo")

    assert Invoice.objects.count() == 8
