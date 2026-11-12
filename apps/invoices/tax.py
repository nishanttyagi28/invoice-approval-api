from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError

TWO_PLACES = Decimal("0.01")


def is_intra_state(vendor, organization):
    return vendor.state_code == organization.state_code


def validate_amounts(*, intra_state, taxable_value, cgst, sgst, igst, total):
    """Check the GST split and the invoice total. Raises ValidationError keyed by field."""
    errors = {}

    if taxable_value <= 0:
        errors["taxable_value"] = "Taxable value must be greater than zero."
    for name, value in (("cgst", cgst), ("sgst", sgst), ("igst", igst)):
        if value < 0:
            errors[name] = "Tax amounts cannot be negative."

    if intra_state and igst:
        errors["igst"] = "Intra-state invoices use CGST and SGST, not IGST."
    if not intra_state and (cgst or sgst):
        errors["cgst"] = "Inter-state invoices use IGST only, not CGST or SGST."

    expected = (taxable_value + cgst + sgst + igst).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    if total != expected:
        errors["total"] = f"Total must equal taxable value plus taxes ({expected})."

    if errors:
        raise ValidationError(errors)
