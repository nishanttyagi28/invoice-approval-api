from rest_framework import serializers


class StatusRowSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=14, decimal_places=2)


class MonthRowSerializer(serializers.Serializer):
    month = serializers.DateField(format="%Y-%m")
    count = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=14, decimal_places=2)


class SummarySerializer(serializers.Serializer):
    by_status = StatusRowSerializer(many=True)
    by_month = MonthRowSerializer(many=True)
