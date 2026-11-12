from django.contrib import admin

from apps.vendors.models import Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "gstin", "state_code", "organization")
    search_fields = ("name", "gstin")
