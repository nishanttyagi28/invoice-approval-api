from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "state_code", "approval_limit")


@admin.register(User)
class OrgUserAdmin(UserAdmin):
    list_display = ("username", "organization", "role", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Organization", {"fields": ("organization", "role")}),)
