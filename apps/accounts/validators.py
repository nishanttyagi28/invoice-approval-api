import re

from django.core.exceptions import ValidationError

STATE_CODE_RE = re.compile(r"^(0[1-9]|[12][0-9]|3[0-8]|97|99)$")


def validate_state_code(value):
    if not STATE_CODE_RE.match(value):
        raise ValidationError("State code must be a two digit GST state code.")
