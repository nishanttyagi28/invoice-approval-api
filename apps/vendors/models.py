from django.db import models

from apps.vendors.validators import validate_gstin


class Vendor(models.Model):
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="vendors"
    )
    name = models.CharField(max_length=200)
    gstin = models.CharField(max_length=15, validators=[validate_gstin])
    state_code = models.CharField(max_length=2, editable=False)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "gstin"], name="unique_vendor_gstin")
        ]

    def __str__(self):
        return f"{self.name} ({self.gstin})"

    def save(self, *args, **kwargs):
        self.state_code = self.gstin[:2]
        super().save(*args, **kwargs)
