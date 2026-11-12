from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Organization, User
from apps.approvals import services
from apps.invoices.models import Invoice
from apps.vendors.models import Vendor

ORG_NAME = "Demo Org (demo data)"
ORG_STATE = "29"
APPROVAL_LIMIT = Decimal("50000.00")
DEMO_PASSWORD = "demo-pass-123"

USERS = {
    "demo_submitter": User.Role.SUBMITTER,
    "demo_approver1": User.Role.APPROVER,
    "demo_approver2": User.Role.APPROVER,
    "demo_finance": User.Role.FINANCE_ADMIN,
}

VENDORS = [
    ("DEMO Sharma Traders", "29AABCS1234A1Z5"),
    ("DEMO Gupta Metals", "27AABCG5678B1Z3"),
    ("DEMO Iyer Electricals", "33AABCI9012C1Z7"),
]

# (vendor index, invoice no, days ago, taxable value, final status)
INVOICES = [
    (0, "DEMO-001", 40, "20000.00", "paid"),
    (1, "DEMO-002", 35, "90000.00", "paid"),
    (2, "DEMO-003", 25, "15000.00", "approved"),
    (0, "DEMO-004", 20, "80000.00", "reviewed"),
    (1, "DEMO-005", 12, "7500.00", "rejected"),
    (2, "DEMO-006", 6, "30000.00", "submitted"),
    (0, "DEMO-007", 3, "12000.00", "submitted"),
    (1, "DEMO-008", 1, "45000.00", "draft"),
]

GST_RATE = Decimal("0.18")


def money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def gst_split(taxable, intra_state):
    tax = money(taxable * GST_RATE)
    if intra_state:
        half = money(taxable * GST_RATE / 2)
        return {"cgst": half, "sgst": half, "igst": Decimal("0.00")}
    return {"cgst": Decimal("0.00"), "sgst": Decimal("0.00"), "igst": tax}


class Command(BaseCommand):
    help = "Create demo vendors and invoices. Everything created is marked as demo data."

    @transaction.atomic
    def handle(self, *args, **options):
        if Organization.objects.filter(name=ORG_NAME).exists():
            self.stdout.write("Demo data already exists, nothing to do.")
            return

        org = Organization.objects.create(
            name=ORG_NAME, state_code=ORG_STATE, approval_limit=APPROVAL_LIMIT
        )
        users = {
            name: User.objects.create_user(
                username=name, password=DEMO_PASSWORD, organization=org, role=role
            )
            for name, role in USERS.items()
        }
        vendors = [
            Vendor.objects.create(organization=org, name=name, gstin=gstin)
            for name, gstin in VENDORS
        ]
        for vendor_index, invoice_no, days_ago, taxable, final in INVOICES:
            invoice = self.create_invoice(
                org, users, vendors[vendor_index], invoice_no, days_ago, taxable
            )
            self.advance(invoice, users, final, days_ago)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created demo data: {len(vendors)} vendors, {len(INVOICES)} invoices. "
                f"Log in as demo_submitter, demo_approver1, demo_approver2 or demo_finance "
                f"with password '{DEMO_PASSWORD}'."
            )
        )

    def create_invoice(self, org, users, vendor, invoice_no, days_ago, taxable):
        taxable = Decimal(taxable)
        taxes = gst_split(taxable, intra_state=vendor.state_code == org.state_code)
        return Invoice.objects.create(
            organization=org,
            vendor=vendor,
            invoice_no=invoice_no,
            invoice_date=timezone.localdate() - timedelta(days=days_ago),
            taxable_value=taxable,
            total=money(taxable + sum(taxes.values())),
            created_by=users["demo_submitter"],
            **taxes,
        )

    def advance(self, invoice, users, final, days_ago):
        if final == "draft":
            return
        services.submit(invoice, users["demo_submitter"], "demo data")
        Invoice.objects.filter(pk=invoice.pk).update(
            submitted_at=timezone.now() - timedelta(days=days_ago)
        )
        first, second = users["demo_approver1"], users["demo_approver2"]
        if final == "rejected":
            services.reject(invoice, first, "demo data: amount does not match the purchase order")
            return
        if final == "submitted":
            return
        services.approve(invoice, first, "demo data")
        if final == "reviewed":
            return
        if invoice.total > invoice.organization.approval_limit:
            services.approve(invoice, second, "demo data")
        if final == "paid":
            services.mark_paid(invoice, users["demo_finance"], "demo data")
