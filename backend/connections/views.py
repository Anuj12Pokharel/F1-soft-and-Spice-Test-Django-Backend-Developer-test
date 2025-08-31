from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db import transaction, IntegrityError
from .models import ConnectionRequest, Connection
from .serializers import ConnectionRequestSerializer, ConnectionSerializer, UserLiteSerializer
from notifications.tasks import send_connection_response_notification
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if isinstance(obj, ConnectionRequest):
            return obj.from_user == request.user or obj.to_user == request.user
        if isinstance(obj, Connection):
            return obj.user1 == request.user or obj.user2 == request.user
        return False

class ConnectionRequestViewSet(viewsets.ModelViewSet):
    queryset = ConnectionRequest.objects.all()
    serializer_class = ConnectionRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = ConnectionRequest.objects.filter(Q(from_user=user) | Q(to_user=user))
        direction = self.request.query_params.get('direction')
        if direction == 'incoming':
            qs = qs.filter(to_user=user)
        elif direction == 'outgoing':
            qs = qs.filter(from_user=user)
        return qs

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        """
        Accept a pending connection request.
        Uses a DB row lock on the request and an atomic get_or_create for Connection
        to avoid race conditions when multiple processes try to accept the same request.
        """
        # Lock the request row to avoid concurrent responders stomping each other
        try:
            with transaction.atomic():
                req = ConnectionRequest.objects.select_for_update().get(pk=pk)
                if req.to_user != request.user:  # Compare objects, not IDs
                    return Response({'detail': 'Only the recipient can accept.'}, status=status.HTTP_403_FORBIDDEN)
                if req.status != ConnectionRequest.STATUS_PENDING:
                    # idempotent: if already accepted/rejected, return appropriate message
                    return Response({'detail': f'Request is not pending (current: {req.status}).'}, status=status.HTTP_400_BAD_REQUEST)

                # determine ordering so connection is stored consistently (user1.user_id < user2.user_id)
                if req.from_user.user_id < req.to_user.user_id:
                    a, b = req.from_user, req.to_user
                else:
                    a, b = req.to_user, req.from_user

                # create connection atomically; handle IntegrityError if concurrent insert occurred
                try:
                    connection, created = Connection.objects.get_or_create(user1=a, user2=b)
                except IntegrityError:
                    # another worker created it in the meantime; fetch existing
                    connection = Connection.objects.filter(user1=a, user2=b).first()

                # mark request accepted
                req.status = ConnectionRequest.STATUS_ACCEPTED
                req.responded_at = timezone.now()
                req.save(update_fields=['status', 'responded_at'])

        except ConnectionRequest.DoesNotExist:
            return Response({'detail': 'Connection request not found.'}, status=status.HTTP_404_NOT_FOUND)

        # send notification asynchronously (don't fail the endpoint if task fails)
        try:
            send_connection_response_notification.delay(
                recipient_id=req.from_user.user_id,  # Use user_id instead of id
                actor_id=req.to_user.user_id,        # Use user_id instead of id
                action='accepted',
                request_id=req.id
            )
        except Exception as e:
            logger.exception("Failed to queue notification task for accept: %s", e)

        return Response({
            'detail': 'Connection accepted.',
            'connection': ConnectionSerializer(connection, context={'request': request}).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        Reject a pending connection request. We lock the request row for consistency.
        """
        try:
            with transaction.atomic():
                req = ConnectionRequest.objects.select_for_update().get(pk=pk)
                if req.to_user != request.user:  # Compare objects, not IDs
                    return Response({'detail': 'Only the recipient can reject.'}, status=status.HTTP_403_FORBIDDEN)
                if req.status != ConnectionRequest.STATUS_PENDING:
                    return Response({'detail': f'Request is not pending (current: {req.status}).'}, status=status.HTTP_400_BAD_REQUEST)

                req.status = ConnectionRequest.STATUS_REJECTED
                req.responded_at = timezone.now()
                req.save(update_fields=['status', 'responded_at'])

        except ConnectionRequest.DoesNotExist:
            return Response({'detail': 'Connection request not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            send_connection_response_notification.delay(
                recipient_id=req.from_user.user_id,  # Use user_id instead of id
                actor_id=req.to_user.user_id,        # Use user_id instead of id
                action='rejected',
                request_id=req.id
            )
        except Exception as e:
            logger.exception("Failed to queue notification task for reject: %s", e)

        return Response({'detail': 'Connection rejected.'}, status=status.HTTP_200_OK)

class ConnectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        return Connection.objects.filter(Q(user1=user) | Q(user2=user))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({'detail': 'Connection removed.'}, status=status.HTTP_204_NO_CONTENT)

class NotificationProxyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Optional: lightweight viewset to show notifications via notifications.serializers.
    If you prefer notifications under their own endpoint, you can ignore this.
    """
    from notifications.serializers import NotificationSerializer
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from notifications.models import Notification
        return Notification.objects.filter(recipient=self.request.user)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_users(request):
    q = request.query_params.get('q', '').strip()
    if not q:
        return Response({'results': []})
    qs = User.objects.filter(
        Q(full_name__icontains=q) |
        Q(company_name__icontains=q) |
        Q(email__icontains=q) |
        Q(contact__icontains=q) |
        Q(username__icontains=q)
    )[:50]
    serializer = UserLiteSerializer(qs, many=True)
    return Response({'results': serializer.data})