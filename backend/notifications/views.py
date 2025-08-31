# notifications/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer
from .permissions import IsRecipientOrReadOnly, IsStaffOrSystemCreateOnly


class NotificationViewSet(viewsets.ModelViewSet):
    """
    Manage notifications:
    - list/retrieve: only the recipient sees their notifications (get_queryset)
    - update/partial_update/destroy: only recipient can modify/delete (IsRecipientOrReadOnly)
    - create: allowed only for staff via API (IsStaffOrSystemCreateOnly); server-side tasks should
      create notifications directly in DB instead of calling this API.
    """
    serializer_class = NotificationSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsRecipientOrReadOnly,
        IsStaffOrSystemCreateOnly,
    ]

    def get_queryset(self):
        # Only show recipient's notifications
        return Notification.objects.filter(recipient=self.request.user)

    def perform_create(self, serializer):
        """
        If an API client creates a notification, set actor to request.user by default.
        Note: serializer should accept a write-only `recipient_id` (and map to a User instance).
        Server-side tasks (Celery) that create Notification objects directly are unaffected.
        """
        serializer.save(actor=self.request.user)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        """
        Mark a single notification as read. Only the recipient may call this (permission enforces it).
        Returns the updated serialized notification.
        """
        notification = self.get_object()
        if notification.read:
            return Response({"detail": "Already marked read."}, status=status.HTTP_200_OK)

        notification.read = True
        notification.save(update_fields=["read"])

        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        """
        Convenience endpoint: mark all unread notifications for the authenticated user as read.
        """
        qs = self.get_queryset().filter(read=False)
        updated_count = qs.update(read=True)
        return Response({"detail": f"{updated_count} notifications marked read."}, status=status.HTTP_200_OK)
