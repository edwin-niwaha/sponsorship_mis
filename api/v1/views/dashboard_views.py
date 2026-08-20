from rest_framework import permissions, viewsets
from rest_framework.response import Response

from api.v1.selectors import dashboard_for_user


class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(dashboard_for_user(request.user))
