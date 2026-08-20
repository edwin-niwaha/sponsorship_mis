from django.db import transaction
from rest_framework import serializers

from apps.users.models import DeviceInstallation


class DeviceInstallationSerializer(serializers.ModelSerializer):
    push_token = serializers.CharField(write_only=True, min_length=20, max_length=512)

    class Meta:
        model = DeviceInstallation
        fields = (
            "id",
            "installation_id",
            "push_token",
            "platform",
            "app_version",
            "notifications_enabled",
            "last_seen_at",
        )
        read_only_fields = ("id", "last_seen_at")

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        push_token = validated_data["push_token"]
        installation, _ = DeviceInstallation.objects.update_or_create(
            user=user,
            installation_id=validated_data["installation_id"],
            defaults={**validated_data, "active": True},
        )
        DeviceInstallation.objects.filter(push_token=push_token).exclude(pk=installation.pk).update(
            active=False,
            notifications_enabled=False,
        )
        return installation
