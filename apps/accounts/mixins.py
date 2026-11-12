class OrganizationScopedMixin:
    """Limit a viewset queryset to the organization of the requesting user."""

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(organization_id=self.request.user.organization_id)
