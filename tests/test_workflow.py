from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.invoices.models import Invoice
from tests.factories import InvoiceFactory, UserFactory

pytestmark = pytest.mark.django_db

Status = Invoice.Status


def act(client_for, user, invoice, action, **data):
    return client_for(user).post(f"/api/invoices/{invoice.id}/{action}/", data, format="json")


@pytest.fixture
def invoice(submitter):
    return InvoiceFactory(created_by=submitter)


@pytest.fixture
def second_approver(org):
    return UserFactory(organization=org, role=User.Role.APPROVER)


@pytest.fixture
def big_invoice(submitter, org):
    """An invoice whose total is above the organization approval limit."""
    org.approval_limit = Decimal("1000.00")
    org.save()
    return InvoiceFactory(created_by=submitter, organization=org)


def test_full_flow_below_limit(client_for, invoice, submitter, approver, finance_admin):
    assert act(client_for, submitter, invoice, "submit").json()["status"] == "submitted"
    assert (
        act(client_for, approver, invoice, "approve", comment="ok").json()["status"] == "approved"
    )
    assert act(client_for, finance_admin, invoice, "mark-paid").json()["status"] == "paid"


def test_submit_only_works_on_a_draft(client_for, invoice, submitter):
    act(client_for, submitter, invoice, "submit")

    assert act(client_for, submitter, invoice, "submit").status_code == 409


def test_only_creator_or_finance_admin_can_submit(client_for, invoice, approver, finance_admin):
    assert act(client_for, approver, invoice, "submit").status_code == 403
    assert act(client_for, finance_admin, invoice, "submit").status_code == 200


def test_creator_cannot_approve_their_own_invoice(client_for, approver):
    own = InvoiceFactory(created_by=approver)
    act(client_for, approver, own, "submit")

    response = act(client_for, approver, own, "approve")

    assert response.status_code == 403
    own.refresh_from_db()
    assert own.status == Status.SUBMITTED


def test_creator_with_finance_admin_role_cannot_approve_own_invoice(client_for, finance_admin):
    own = InvoiceFactory(created_by=finance_admin)
    act(client_for, finance_admin, own, "submit")

    assert act(client_for, finance_admin, own, "approve").status_code == 403


def test_submitter_role_cannot_approve(client_for, invoice, submitter, org):
    act(client_for, submitter, invoice, "submit")
    other_submitter = UserFactory(organization=org, role=User.Role.SUBMITTER)

    assert act(client_for, other_submitter, invoice, "approve").status_code == 403


def test_one_approval_is_enough_at_or_below_the_limit(client_for, invoice, submitter, approver):
    invoice.organization.approval_limit = invoice.total
    invoice.organization.save()
    act(client_for, submitter, invoice, "submit")

    assert act(client_for, approver, invoice, "approve").json()["status"] == "approved"


def test_above_limit_needs_two_different_approvers(
    client_for, big_invoice, submitter, approver, second_approver
):
    act(client_for, submitter, big_invoice, "submit")

    first = act(client_for, approver, big_invoice, "approve")
    second = act(client_for, second_approver, big_invoice, "approve")

    assert first.json()["status"] == "reviewed"
    assert second.json()["status"] == "approved"


def test_same_approver_cannot_approve_twice(client_for, big_invoice, submitter, approver):
    act(client_for, submitter, big_invoice, "submit")
    act(client_for, approver, big_invoice, "approve")

    response = act(client_for, approver, big_invoice, "approve")

    assert response.status_code == 409
    big_invoice.refresh_from_db()
    assert big_invoice.status == Status.REVIEWED


def test_reject_from_submitted(client_for, invoice, submitter, approver):
    act(client_for, submitter, invoice, "submit")

    response = act(client_for, approver, invoice, "reject", comment="wrong gstin")

    assert response.json()["status"] == "rejected"


def test_reject_after_first_approval(client_for, big_invoice, submitter, approver, second_approver):
    act(client_for, submitter, big_invoice, "submit")
    act(client_for, approver, big_invoice, "approve")

    response = act(client_for, second_approver, big_invoice, "reject")

    assert response.json()["status"] == "rejected"


def test_rejected_invoice_cannot_be_approved_or_paid(
    client_for, invoice, submitter, approver, finance_admin
):
    act(client_for, submitter, invoice, "submit")
    act(client_for, approver, invoice, "reject")

    assert act(client_for, finance_admin, invoice, "approve").status_code == 409
    assert act(client_for, finance_admin, invoice, "mark-paid").status_code == 409


def test_draft_cannot_be_approved(client_for, invoice, approver):
    assert act(client_for, approver, invoice, "approve").status_code == 409


def test_only_finance_admin_can_mark_paid(client_for, invoice, submitter, approver):
    act(client_for, submitter, invoice, "submit")
    act(client_for, approver, invoice, "approve")

    assert act(client_for, approver, invoice, "mark-paid").status_code == 403


def test_mark_paid_needs_an_approved_invoice(client_for, invoice, submitter, finance_admin):
    act(client_for, submitter, invoice, "submit")

    assert act(client_for, finance_admin, invoice, "mark-paid").status_code == 409


def test_paid_invoice_cannot_be_changed_by_any_action(
    client_for, invoice, submitter, approver, finance_admin
):
    act(client_for, submitter, invoice, "submit")
    act(client_for, approver, invoice, "approve")
    act(client_for, finance_admin, invoice, "mark-paid")

    for user, action in [(approver, "approve"), (approver, "reject"), (finance_admin, "mark-paid")]:
        assert act(client_for, user, invoice, action).status_code == 409
    invoice.refresh_from_db()
    assert invoice.status == Status.PAID


def test_actions_on_another_organizations_invoice_are_not_found(client_for, approver):
    foreign = InvoiceFactory(status=Status.SUBMITTED)

    assert act(client_for, approver, foreign, "approve").status_code == 404
