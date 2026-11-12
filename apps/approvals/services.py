from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.approvals.exceptions import InvalidTransition
from apps.approvals.models import Approval, AuditLog
from apps.invoices.models import Invoice

Status = Invoice.Status


def required_approvals(invoice):
    """Totals above the organization limit need two different approvers."""
    return 2 if invoice.total > invoice.organization.approval_limit else 1


def _lock(invoice):
    return Invoice.objects.select_for_update().select_related("organization").get(pk=invoice.pk)


def _move(invoice, actor, to_status, *, comment="", **extra):
    from_status = invoice.status
    invoice.status = to_status
    invoice.save(update_fields=["status", "submitted_at", "updated_at"])
    metadata = {"comment": comment, **extra}
    AuditLog.objects.create(
        actor=actor,
        invoice=invoice,
        from_status=from_status,
        to_status=to_status,
        metadata=metadata,
    )
    return invoice


def _ensure_status(invoice, *allowed):
    if invoice.status not in allowed:
        raise InvalidTransition(f"Invoice is {invoice.status}; this action is not allowed now.")


def _ensure_reviewer(invoice, actor):
    if invoice.created_by_id == actor.id:
        raise PermissionDenied("You cannot review an invoice you created.")
    if invoice.approvals.filter(approver=actor).exists():
        raise InvalidTransition("You have already recorded a decision on this invoice.")


@transaction.atomic
def submit(invoice, actor, comment=""):
    invoice = _lock(invoice)
    if invoice.created_by_id != actor.id and actor.role != User.Role.FINANCE_ADMIN:
        raise PermissionDenied("Only the creator or a finance admin can submit this invoice.")
    _ensure_status(invoice, Status.DRAFT)
    invoice.submitted_at = timezone.now()
    return _move(invoice, actor, Status.SUBMITTED, comment=comment)


@transaction.atomic
def approve(invoice, actor, comment=""):
    invoice = _lock(invoice)
    _ensure_status(invoice, Status.SUBMITTED, Status.REVIEWED)
    _ensure_reviewer(invoice, actor)
    Approval.objects.create(
        invoice=invoice, approver=actor, decision=Approval.Decision.APPROVED, comment=comment
    )
    approved = invoice.approvals.filter(decision=Approval.Decision.APPROVED).count()
    required = required_approvals(invoice)
    to_status = Status.APPROVED if approved >= required else Status.REVIEWED
    return _move(invoice, actor, to_status, comment=comment, approvals=approved, required=required)


@transaction.atomic
def reject(invoice, actor, comment=""):
    invoice = _lock(invoice)
    _ensure_status(invoice, Status.SUBMITTED, Status.REVIEWED)
    _ensure_reviewer(invoice, actor)
    Approval.objects.create(
        invoice=invoice, approver=actor, decision=Approval.Decision.REJECTED, comment=comment
    )
    return _move(invoice, actor, Status.REJECTED, comment=comment)


@transaction.atomic
def mark_paid(invoice, actor, comment=""):
    invoice = _lock(invoice)
    _ensure_status(invoice, Status.APPROVED)
    return _move(invoice, actor, Status.PAID, comment=comment)
