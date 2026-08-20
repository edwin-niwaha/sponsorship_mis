from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response

from api.v1.serializers.feedback_serializers import FeedbackSerializer


class FeedbackViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FeedbackSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Thank you. Your feedback has been sent."},
            status=status.HTTP_201_CREATED,
        )
