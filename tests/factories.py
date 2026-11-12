from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import Organization, User
from apps.invoices.models import Invoice
from apps.vendors.models import Vendor

PASSWORD = "test-pass-123"


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f"Org {n}")
    state_code = "29"
    approval_limit = Decimal("50000.00")


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    organization = factory.SubFactory(OrganizationFactory)
    role = User.Role.SUBMITTER

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.objects.create_user(*args, password=PASSWORD, **kwargs)


class VendorFactory(DjangoModelFactory):
    class Meta:
        model = Vendor

    class Params:
        state = "29"

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Vendor {n}")
    gstin = factory.LazyAttributeSequence(lambda o, n: f"{o.state}AABCU{n:04d}A1Z5")


class InvoiceFactory(DjangoModelFactory):
    class Meta:
        model = Invoice

    created_by = factory.SubFactory(UserFactory)
    organization = factory.SelfAttribute("created_by.organization")
    vendor = factory.SubFactory(VendorFactory, organization=factory.SelfAttribute("..organization"))
    invoice_no = factory.Sequence(lambda n: f"INV-{n:04d}")
    invoice_date = date(2026, 10, 1)
    taxable_value = Decimal("1000.00")
    cgst = Decimal("90.00")
    sgst = Decimal("90.00")
    igst = Decimal("0.00")
    total = Decimal("1180.00")
