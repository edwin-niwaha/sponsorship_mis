from rest_framework import permissions, viewsets

from api.v1.serializers import DeviceInstallationSerializer
from apps.users.models import DeviceInstallation


class DeviceInstallationViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceInstallationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return DeviceInstallation.objects.none()
        return DeviceInstallation.objects.filter(user=self.request.user, active=True).order_by("-last_seen_at")

    def perform_destroy(self, instance):
        instance.active = False
        instance.notifications_enabled = False
        instance.save(update_fields=("active", "notifications_enabled", "last_seen_at"))
