from django_filters import rest_framework as filters

from apps.invoices.models import Invoice


class InvoiceFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="invoice_date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="invoice_date", lookup_expr="lte")

    class Meta:
        model = Invoice
        fields = ["status", "vendor"]
