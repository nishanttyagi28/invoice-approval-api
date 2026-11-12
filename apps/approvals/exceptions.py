from rest_framework import status
from rest_framework.exceptions import APIException


class InvalidTransition(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "invalid_transition"
    default_detail = "The invoice is not in a state that allows this action."
