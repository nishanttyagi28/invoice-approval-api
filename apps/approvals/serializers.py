from rest_framework import serializers

from apps.approvals.models import AuditLog


class ActionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "from_status", "to_status", "timestamp", "metadata"]
        read_only_fields = fields
