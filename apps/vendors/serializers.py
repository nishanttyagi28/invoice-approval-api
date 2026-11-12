from rest_framework import serializers

from apps.vendors.models import Vendor
from apps.vendors.validators import validate_gstin


class VendorSerializer(serializers.ModelSerializer):
    gstin = serializers.CharField(max_length=15, validators=[validate_gstin])

    class Meta:
        model = Vendor
        fields = ["id", "name", "gstin", "state_code"]
        read_only_fields = ["state_code"]

    def validate_gstin(self, value):
        organization = self.context["request"].user.organization
        duplicates = Vendor.objects.filter(organization=organization, gstin=value)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A vendor with this GSTIN already exists.")
        return value
