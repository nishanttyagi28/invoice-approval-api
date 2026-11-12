from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.invoices.tax import validate_amounts

D = Decimal


def check(intra_state, taxable, cgst, sgst, igst, total):
    validate_amounts(
        intra_state=intra_state,
        taxable_value=D(taxable),
        cgst=D(cgst),
        sgst=D(sgst),
        igst=D(igst),
        total=D(total),
    )


def error_fields(*args):
    with pytest.raises(ValidationError) as exc:
        check(*args)
    return set(exc.value.message_dict)


def test_intra_state_with_cgst_and_sgst_is_valid():
    check(True, "1000.00", "90.00", "90.00", "0", "1180.00")


def test_inter_state_with_igst_is_valid():
    check(False, "1000.00", "0", "0", "180.00", "1180.00")


def test_intra_state_rejects_igst():
    assert "igst" in error_fields(True, "1000.00", "0", "0", "180.00", "1180.00")


def test_inter_state_rejects_cgst_and_sgst():
    assert "cgst" in error_fields(False, "1000.00", "90.00", "90.00", "0", "1180.00")


def test_cgst_sgst_and_igst_together_are_rejected():
    assert "igst" in error_fields(True, "1000.00", "90.00", "90.00", "180.00", "1360.00")


def test_total_must_match_taxable_value_plus_taxes():
    assert error_fields(True, "1000.00", "90.00", "90.00", "0", "1200.00") == {"total"}


def test_total_is_compared_after_rounding_to_two_decimals():
    check(True, "10.005", "0", "0", "0", "10.01")
    assert error_fields(True, "10.005", "0", "0", "0", "10.00") == {"total"}


def test_taxable_value_must_be_positive():
    assert "taxable_value" in error_fields(True, "0", "0", "0", "0", "0")
