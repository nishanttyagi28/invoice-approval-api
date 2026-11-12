import json
from contextlib import nullcontext
from datetime import timedelta
from urllib.error import URLError

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals import reminders
from apps.approvals.tasks import send_pending_reminders
from apps.invoices.models import Invoice
from config import celery_app
from tests.factories import InvoiceFactory, OrganizationFactory, UserFactory

pytestmark = pytest.mark.django_db

Status = Invoice.Status


def pending_invoice(hours_ago, status=Status.SUBMITTED, **kwargs):
    submitted_at = timezone.now() - timedelta(hours=hours_ago)
    return InvoiceFactory(status=status, submitted_at=submitted_at, **kwargs)


@pytest.fixture
def approver_with_email(org):
    return UserFactory(organization=org, role=User.Role.APPROVER, email="approver@example.com")


def test_invoice_pending_for_more_than_48_hours_is_reminded(org, approver_with_email):
    old = pending_invoice(49, created_by=UserFactory(organization=org))

    reminded = send_pending_reminders()

    assert reminded == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["approver@example.com"]
    assert old.invoice_no in mail.outbox[0].body
    old.refresh_from_db()
    assert old.last_reminded_at is not None


def test_recent_invoice_is_not_reminded(org, approver_with_email):
    pending_invoice(47, created_by=UserFactory(organization=org))

    assert send_pending_reminders() == 0
    assert mail.outbox == []


@pytest.mark.parametrize("status", [Status.DRAFT, Status.APPROVED, Status.REJECTED, Status.PAID])
def test_only_submitted_and_reviewed_invoices_are_reminded(org, approver_with_email, status):
    pending_invoice(100, status=status, created_by=UserFactory(organization=org))

    assert send_pending_reminders() == 0


def test_reviewed_invoice_is_reminded_too(org, approver_with_email):
    pending_invoice(60, status=Status.REVIEWED, created_by=UserFactory(organization=org))

    assert send_pending_reminders() == 1


def test_invoice_is_not_reminded_again_within_48_hours(org, approver_with_email):
    pending_invoice(72, created_by=UserFactory(organization=org))
    send_pending_reminders()

    assert send_pending_reminders() == 0
    assert len(mail.outbox) == 1


def test_invoice_is_reminded_again_after_48_hours(org, approver_with_email):
    invoice = pending_invoice(200, created_by=UserFactory(organization=org))
    Invoice.objects.filter(pk=invoice.pk).update(
        last_reminded_at=timezone.now() - timedelta(hours=49)
    )

    assert send_pending_reminders() == 1


def test_reminder_goes_only_to_approvers_of_the_same_organization(org, approver_with_email):
    other_org = OrganizationFactory()
    UserFactory(organization=other_org, role=User.Role.APPROVER, email="other@example.com")
    pending_invoice(50, created_by=UserFactory(organization=org))

    send_pending_reminders()

    assert [m.to for m in mail.outbox] == [["approver@example.com"]]


def test_no_recipients_and_no_webhook_means_no_reminder_is_recorded(org):
    invoice = pending_invoice(50, created_by=UserFactory(organization=org))

    assert send_pending_reminders() == 0
    invoice.refresh_from_db()
    assert invoice.last_reminded_at is None


def test_webhook_receives_the_pending_invoices(org, monkeypatch):
    org.webhook_url = "https://hooks.example.com/pending"
    org.save()
    invoice = pending_invoice(50, created_by=UserFactory(organization=org))
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, json.loads(request.data)))
        return nullcontext()

    monkeypatch.setattr(reminders, "urlopen", fake_urlopen)

    assert send_pending_reminders() == 1
    url, body = calls[0]
    assert url == "https://hooks.example.com/pending"
    assert body["invoices"][0]["invoice_no"] == invoice.invoice_no


def test_failed_webhook_does_not_mark_invoice_as_reminded(org, monkeypatch):
    org.webhook_url = "https://hooks.example.com/pending"
    org.save()
    invoice = pending_invoice(50, created_by=UserFactory(organization=org))

    def broken_urlopen(request, timeout):
        raise URLError("unreachable")

    monkeypatch.setattr(reminders, "urlopen", broken_urlopen)

    assert send_pending_reminders() == 0
    invoice.refresh_from_db()
    assert invoice.last_reminded_at is None


def test_task_is_registered_and_scheduled_with_celery_beat():
    schedule = celery_app.conf.beat_schedule["pending-invoice-reminders"]

    assert schedule["task"] in celery_app.tasks
    assert schedule["task"] == "apps.approvals.tasks.send_pending_reminders"
