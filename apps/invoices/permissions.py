from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User


class IsOrganizationMember(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.organization_id)


class CreatorOrFinanceAdminCanWrite(BasePermission):
    message = "Only the creator or a finance admin can change this invoice."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return user.role == User.Role.FINANCE_ADMIN or obj.created_by_id == user.id
