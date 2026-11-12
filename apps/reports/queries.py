from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from apps.invoices.models import Invoice


def summary_for(organization_id):
    invoices = Invoice.objects.filter(organization_id=organization_id)
    aggregates = {"count": Count("id"), "total": Sum("total")}

    by_status = invoices.values("status").annotate(**aggregates).order_by("status")
    by_month = (
        invoices.annotate(month=TruncMonth("invoice_date"))
        .values("month")
        .annotate(**aggregates)
        .order_by("month")
    )
    return {"by_status": list(by_status), "by_month": list(by_month)}
