from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.accounts.validators import validate_state_code


class Organization(models.Model):
    name = models.CharField(max_length=200, unique=True)
    state_code = models.CharField(max_length=2, validators=[validate_state_code])
    approval_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("50000.00"),
        help_text="Invoices with a total above this amount need two different approvers.",
    )

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        SUBMITTER = "submitter", "Submitter"
        APPROVER = "approver", "Approver"
        FINANCE_ADMIN = "finance_admin", "Finance admin"

    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="users", null=True
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SUBMITTER)
