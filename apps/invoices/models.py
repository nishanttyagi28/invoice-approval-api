from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


def money_field():
    return models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="invoices"
    )
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.PROTECT, related_name="invoices")
    invoice_no = models.CharField(max_length=50)
    invoice_date = models.DateField()
    taxable_value = money_field()
    cgst = money_field()
    sgst = money_field()
    igst = money_field()
    total = money_field()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="created_invoices"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-invoice_date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["vendor", "invoice_no"], name="unique_invoice_no")
        ]
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self):
        return f"{self.invoice_no} ({self.vendor_id})"

    def save(self, *args, **kwargs):
        if self.pk and Invoice.objects.filter(pk=self.pk, status=self.Status.PAID).exists():
            raise ValidationError("Paid invoices cannot be edited.")
        super().save(*args, **kwargs)

    @property
    def is_editable(self):
        return self.status == self.Status.DRAFT
