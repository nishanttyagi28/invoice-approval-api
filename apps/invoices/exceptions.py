from rest_framework import status
from rest_framework.exceptions import APIException


class InvoiceLocked(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "invoice_locked"
