from decimal import Decimal

from rest_framework import serializers

from apps.invoices.models import Invoice
from apps.invoices.tax import is_intra_state, validate_amounts
from apps.vendors.models import Vendor

AMOUNT_FIELDS = ["taxable_value", "cgst", "sgst", "igst", "total"]


class OrganizationVendorField(serializers.PrimaryKeyRelatedField):
    """Only vendors of the requesting user's organization can be picked."""

    def get_queryset(self):
        request = self.context.get("request")
        if request is None:
            return Vendor.objects.none()
        return Vendor.objects.filter(organization_id=request.user.organization_id)


class InvoiceSerializer(serializers.ModelSerializer):
    vendor = OrganizationVendorField(queryset=Vendor.objects.all())
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "vendor",
            "vendor_name",
            "invoice_no",
            "invoice_date",
            *AMOUNT_FIELDS,
            "status",
            "created_by",
            "submitted_at",
            "created_at",
        ]
        read_only_fields = ["status", "created_by", "submitted_at", "created_at"]
        validators = []

    def _current(self, attrs, name):
        if name in attrs:
            return attrs[name]
        if self.instance is not None:
            return getattr(self.instance, name)
        return Decimal("0.00")

    def validate(self, attrs):
        organization = self.context["request"].user.organization
        vendor = attrs.get("vendor") or self.instance.vendor
        invoice_no = attrs.get("invoice_no", getattr(self.instance, "invoice_no", None))

        duplicates = Invoice.objects.filter(vendor=vendor, invoice_no=invoice_no)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                {"invoice_no": "This vendor already has an invoice with this number."}
            )

        validate_amounts(
            intra_state=is_intra_state(vendor, organization),
            **{name: self._current(attrs, name) for name in AMOUNT_FIELDS},
        )
        return attrs
