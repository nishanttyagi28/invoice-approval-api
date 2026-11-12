import re

from django.core.exceptions import ValidationError

GSTIN_RE = re.compile(r"^(0[1-9]|[12][0-9]|3[0-8]|97|99)[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def validate_gstin(value):
    if not GSTIN_RE.match(value):
        raise ValidationError(
            "GSTIN must be 15 characters: 2 digit state code, 10 character PAN, "
            "entity number, 'Z' and a check character."
        )
