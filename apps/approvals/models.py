from django.db import models


class AuditLogImmutable(Exception):
    """Raised on any attempt to change or remove an audit log entry."""


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AuditLogImmutable("Audit log entries cannot be updated.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise AuditLogImmutable("Audit log entries cannot be updated.")

    def delete(self):
        raise AuditLogImmutable("Audit log entries cannot be deleted.")


class Approval(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    invoice = models.ForeignKey(
        "invoices.Invoice", on_delete=models.CASCADE, related_name="approvals"
    )
    approver = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="approvals"
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["invoice", "approver"], name="one_decision_per_approver"
            )
        ]

    def __str__(self):
        return f"{self.decision} by {self.approver_id} on invoice {self.invoice_id}"


class AuditLog(models.Model):
    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    invoice = models.ForeignKey(
        "invoices.Invoice", on_delete=models.PROTECT, related_name="audit_logs"
    )
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ["timestamp", "id"]

    def __str__(self):
        return f"invoice {self.invoice_id}: {self.from_status} -> {self.to_status}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditLogImmutable("Audit log entries cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditLogImmutable("Audit log entries cannot be deleted.")
