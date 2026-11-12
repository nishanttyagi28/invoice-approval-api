from rest_framework import viewsets

from apps.accounts.mixins import OrganizationScopedMixin
from apps.accounts.permissions import ReadOnlyOrFinanceAdmin
from apps.vendors.models import Vendor
from apps.vendors.serializers import VendorSerializer


class VendorViewSet(OrganizationScopedMixin, viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [ReadOnlyOrFinanceAdmin]
    filterset_fields = ["state_code"]
    search_fields = ["name", "gstin"]
    ordering_fields = ["name"]

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
