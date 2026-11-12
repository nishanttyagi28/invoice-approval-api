from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsApprover, IsFinanceAdmin
from apps.approvals import services
from apps.approvals.models import AuditLog
from apps.approvals.serializers import ActionSerializer, AuditLogSerializer
from apps.invoices.models import Invoice
from apps.invoices.permissions import IsOrganizationMember
from apps.invoices.serializers import InvoiceSerializer


def organization_invoices(request):
    return Invoice.objects.select_related("vendor").filter(
        organization_id=request.user.organization_id
    )


class InvoiceActionView(APIView):
    """Base for the POST actions that move an invoice to its next status."""

    permission_classes = [IsOrganizationMember]
    serializer_class = ActionSerializer
    service = None

    @extend_schema(request=ActionSerializer, responses=InvoiceSerializer)
    def post(self, request, pk):
        invoice = get_object_or_404(organization_invoices(request), pk=pk)
        data = ActionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        invoice = self.service(invoice, request.user, data.validated_data["comment"])
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)


class SubmitView(InvoiceActionView):
    service = staticmethod(services.submit)


class ApproveView(InvoiceActionView):
    permission_classes = [IsOrganizationMember, IsApprover]
    service = staticmethod(services.approve)


class RejectView(InvoiceActionView):
    permission_classes = [IsOrganizationMember, IsApprover]
    service = staticmethod(services.reject)


class MarkPaidView(InvoiceActionView):
    permission_classes = [IsOrganizationMember, IsFinanceAdmin]
    service = staticmethod(services.mark_paid)


class InvoiceAuditView(generics.ListAPIView):
    permission_classes = [IsOrganizationMember]
    serializer_class = AuditLogSerializer
    filter_backends = []

    def get_queryset(self):
        invoice = get_object_or_404(organization_invoices(self.request), pk=self.kwargs["pk"])
        return AuditLog.objects.filter(invoice=invoice).select_related("actor")
