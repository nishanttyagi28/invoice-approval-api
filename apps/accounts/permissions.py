from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User


def has_role(*roles):
    """Build a permission class that allows only the given roles."""

    class HasRole(BasePermission):
        message = "Your role is not allowed to do this."

        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and user.role in roles)

    return HasRole


IsApprover = has_role(User.Role.APPROVER, User.Role.FINANCE_ADMIN)
IsFinanceAdmin = has_role(User.Role.FINANCE_ADMIN)


class ReadOnlyOrFinanceAdmin(BasePermission):
    """Everyone in the org can read, only finance admins can write."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.organization_id):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role == User.Role.FINANCE_ADMIN
