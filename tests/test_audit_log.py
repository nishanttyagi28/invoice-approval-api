import pytest

from apps.approvals.models import AuditLog, AuditLogImmutable
from tests.factories import InvoiceFactory, UserFactory

pytestmark = pytest.mark.django_db


def act(client_for, user, invoice, action, **data):
    return client_for(user).post(f"/api/invoices/{invoice.id}/{action}/", data, format="json")


@pytest.fixture
def entry(submitter):
    invoice = InvoiceFactory(created_by=submitter)
    return AuditLog.objects.create(
        actor=submitter, invoice=invoice, from_status="draft", to_status="submitted"
    )


def test_every_state_change_is_logged(client_for, submitter, approver, finance_admin):
    invoice = InvoiceFactory(created_by=submitter)
    act(client_for, submitter, invoice, "submit")
    act(client_for, approver, invoice, "approve", comment="looks fine")
    act(client_for, finance_admin, invoice, "mark-paid")

    rows = list(AuditLog.objects.filter(invoice=invoice).values_list("from_status", "to_status"))
    actors = list(AuditLog.objects.filter(invoice=invoice).values_list("actor", flat=True))

    assert rows == [("draft", "submitted"), ("submitted", "approved"), ("approved", "paid")]
    assert actors == [submitter.id, approver.id, finance_admin.id]


def test_metadata_keeps_the_comment_and_approval_counts(client_for, submitter, approver):
    invoice = InvoiceFactory(created_by=submitter)
    act(client_for, submitter, invoice, "submit")
    act(client_for, approver, invoice, "approve", comment="looks fine")

    last = AuditLog.objects.filter(invoice=invoice).last()

    assert last.metadata == {"comment": "looks fine", "approvals": 1, "required": 1}


def test_failed_action_leaves_no_log_entry(client_for, submitter, approver):
    invoice = InvoiceFactory(created_by=submitter)

    act(client_for, approver, invoice, "approve")

    assert AuditLog.objects.count() == 0


def test_audit_entry_cannot_be_saved_again(entry):
    entry.to_status = "paid"

    with pytest.raises(AuditLogImmutable):
        entry.save()


def test_audit_entry_cannot_be_deleted(entry):
    with pytest.raises(AuditLogImmutable):
        entry.delete()


def test_audit_queryset_blocks_bulk_update_and_delete(entry):
    with pytest.raises(AuditLogImmutable):
        AuditLog.objects.update(to_status="paid")
    with pytest.raises(AuditLogImmutable):
        AuditLog.objects.all().delete()
    assert AuditLog.objects.count() == 1


def test_audit_endpoint_lists_entries_in_order(client_for, submitter, approver):
    invoice = InvoiceFactory(created_by=submitter)
    act(client_for, submitter, invoice, "submit")
    act(client_for, approver, invoice, "approve")

    response = client_for(submitter).get(f"/api/invoices/{invoice.id}/audit/")

    body = response.json()["results"]
    assert [(e["from_status"], e["to_status"]) for e in body] == [
        ("draft", "submitted"),
        ("submitted", "approved"),
    ]
    assert body[0]["actor"] == submitter.username


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_audit_endpoint_is_read_only(client_for, submitter, entry, method):
    client = client_for(submitter)

    response = getattr(client, method)(f"/api/invoices/{entry.invoice_id}/audit/")

    assert response.status_code == 405


def test_audit_endpoint_hides_other_organizations(client_for, entry):
    outsider = UserFactory()

    response = client_for(outsider).get(f"/api/invoices/{entry.invoice_id}/audit/")

    assert response.status_code == 404
