from rest_framework import viewsets

from apps.accounts.mixins import OrganizationScopedMixin
from apps.invoices.exceptions import InvoiceLocked
from apps.invoices.filters import InvoiceFilter
from apps.invoices.models import Invoice
from apps.invoices.permissions import CreatorOrFinanceAdminCanWrite, IsOrganizationMember
from apps.invoices.serializers import InvoiceSerializer


class InvoiceViewSet(OrganizationScopedMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("vendor", "created_by")
    serializer_class = InvoiceSerializer
    permission_classes = [IsOrganizationMember, CreatorOrFinanceAdminCanWrite]
    filterset_class = InvoiceFilter
    search_fields = ["invoice_no", "vendor__name"]
    ordering_fields = ["invoice_date", "total", "created_at"]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(organization=user.organization, created_by=user)

    def perform_update(self, serializer):
        self._ensure_editable(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_editable(instance)
        instance.delete()

    @staticmethod
    def _ensure_editable(invoice):
        if invoice.status == Invoice.Status.PAID:
            raise InvoiceLocked("Paid invoices cannot be edited.")
        if not invoice.is_editable:
            raise InvoiceLocked("Only draft invoices can be edited or deleted.")
