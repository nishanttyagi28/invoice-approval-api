from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsApprover
from apps.invoices.permissions import IsOrganizationMember
from apps.reports.queries import summary_for
from apps.reports.serializers import SummarySerializer


class SummaryView(APIView):
    permission_classes = [IsOrganizationMember, IsApprover]

    @extend_schema(responses=SummarySerializer)
    def get(self, request):
        data = summary_for(request.user.organization_id)
        return Response(SummarySerializer(data).data)
