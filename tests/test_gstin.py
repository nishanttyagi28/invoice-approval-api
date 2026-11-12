import pytest
from django.core.exceptions import ValidationError

from apps.vendors.validators import validate_gstin


@pytest.mark.parametrize("gstin", ["29AABCU9603R1ZX", "07AAACG1234A1Z5", "27AAPFU0939F1ZV"])
def test_valid_gstin_passes(gstin):
    validate_gstin(gstin)


@pytest.mark.parametrize(
    "gstin",
    [
        "29AABCU9603R1Z",  # 14 characters
        "29AABCU9603R1ZXX",  # 16 characters
        "29aabcu9603r1zx",  # lowercase
        "00AABCU9603R1ZX",  # state code 00
        "29AABCU9603R1AX",  # 14th character must be Z
        "2AAABCU96031R1Z",  # PAN part in wrong place
        "",
    ],
)
def test_invalid_gstin_is_rejected(gstin):
    with pytest.raises(ValidationError):
        validate_gstin(gstin)
