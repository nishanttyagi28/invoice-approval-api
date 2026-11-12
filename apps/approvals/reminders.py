import json
import logging
from datetime import timedelta
from itertools import groupby
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.invoices.models import Invoice

logger = logging.getLogger(__name__)

PENDING_STATUSES = [Invoice.Status.SUBMITTED, Invoice.Status.REVIEWED]


def invoices_needing_reminder():
    """Invoices pending for more than the reminder window and not reminded within it."""
    cutoff = timezone.now() - timedelta(hours=settings.REMINDER_AFTER_HOURS)
    return (
        Invoice.objects.filter(status__in=PENDING_STATUSES, submitted_at__lte=cutoff)
        .filter(Q(last_reminded_at__isnull=True) | Q(last_reminded_at__lte=cutoff))
        .select_related("organization", "vendor")
        .order_by("organization_id", "submitted_at")
    )


def _describe(invoices):
    return [
        {
            "id": invoice.id,
            "invoice_no": invoice.invoice_no,
            "vendor": invoice.vendor.name,
            "total": str(invoice.total),
            "status": invoice.status,
            "submitted_at": invoice.submitted_at.isoformat(),
        }
        for invoice in invoices
    ]


def email_approvers(organization, invoices):
    recipients = list(
        User.objects.filter(
            organization=organization,
            role__in=[User.Role.APPROVER, User.Role.FINANCE_ADMIN],
            is_active=True,
        )
        .exclude(email="")
        .values_list("email", flat=True)
    )
    if not recipients:
        return False
    lines = [f"- {i['invoice_no']} ({i['vendor']}), {i['total']}, {i['status']}" for i in invoices]
    body = (
        f"These invoices have been waiting for more than {settings.REMINDER_AFTER_HOURS} hours:\n\n"
        + "\n".join(lines)
    )
    send_mail("Invoices waiting for approval", body, settings.DEFAULT_FROM_EMAIL, recipients)
    return True


def post_webhook(organization, invoices):
    if not organization.webhook_url:
        return False
    payload = json.dumps({"organization": organization.name, "invoices": invoices}).encode()
    request = Request(
        organization.webhook_url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urlopen(request, timeout=5):
            return True
    except (URLError, ValueError, OSError):
        logger.warning("Reminder webhook failed for organization %s", organization.pk)
        return False


def send_reminders():
    """Notify each organization about its stale invoices. Returns how many were reminded."""
    reminded = 0
    for _, group in groupby(invoices_needing_reminder(), key=lambda i: i.organization_id):
        invoices = list(group)
        organization = invoices[0].organization
        details = _describe(invoices)
        emailed = email_approvers(organization, details)
        posted = post_webhook(organization, details)
        if emailed or posted:
            Invoice.objects.filter(pk__in=[i.pk for i in invoices]).update(
                last_reminded_at=timezone.now()
            )
            reminded += len(invoices)
    return reminded
