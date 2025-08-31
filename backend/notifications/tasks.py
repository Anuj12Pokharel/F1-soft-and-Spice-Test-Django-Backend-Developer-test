# notifications/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True)
def send_connection_response_notification(self, recipient_id, actor_id=None, action='notified', request_id=None):
    """
    Creates a Notification for `recipient_id` about `actor_id` performing `action`,
    and attempts to push it via Channels to the recipient's group `user_<user_id>`.

    Returns a dict with status and (when available) serialized notification.
    """
    # Lookup recipient using custom user_id field
    try:
        recipient = User.objects.get(user_id=recipient_id)
    except User.DoesNotExist:
        logger.warning("Notification task: recipient not found: %s", recipient_id)
        return {'status': 'error', 'reason': 'recipient_not_found', 'recipient_id': recipient_id}

    actor = None
    if actor_id:
        try:
            actor = User.objects.get(user_id=actor_id)
        except User.DoesNotExist:
            # actor is optional; continue with None
            actor = None

    # Build verb/message
    if action == 'accepted':
        verb = 'accepted your connection request'
        message = f"{actor.username if actor else 'Someone'} accepted your connection request."
    elif action == 'rejected':
        verb = 'rejected your connection request'
        message = f"{actor.username if actor else 'Someone'} rejected your connection request."
    else:
        verb = str(action)
        message = f"{actor.username if actor else 'Someone'}: {action}"

    try:
        notif = Notification.objects.create(
            recipient=recipient,
            actor=actor,
            verb=verb,
            message=message,
            # created_at is auto set by model's auto_now_add=True
        )
    except Exception as exc:
        logger.exception("Failed to create Notification for recipient %s: %s", recipient_id, exc)
        return {'status': 'error', 'reason': 'db_error', 'details': str(exc)}

    # Serialize the notification for sending to clients
    try:
        serialized = NotificationSerializer(notif, context={}).data
    except Exception as exc:
        logger.exception("Failed to serialize Notification id=%s: %s", getattr(notif, 'id', None), exc)
        serialized = {
            'id': getattr(notif, 'id', None),
            'recipient': getattr(recipient, 'user_id', None),
            'actor': getattr(actor, 'user_id', None) if actor else None,
            'verb': verb,
            'message': message,
            'read': notif.read,
            'created_at': notif.created_at.isoformat() if getattr(notif, 'created_at', None) else timezone.now().isoformat(),
        }

    # Attempt to push via Channels to the recipient's group
    try:
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            group_name = f"user_{recipient.user_id}"  # ensure this matches your consumer's group naming
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "notification.message",  # consumer must implement notification_message handler
                    "notification": serialized,
                }
            )
        else:
            logger.debug("Channel layer not configured; skipping push for notification id=%s", getattr(notif, 'id', None))
    except Exception as exc:
        # Do not fail the task if push fails; notification is persisted in DB
        logger.exception("Failed to push Notification id=%s via Channels: %s", getattr(notif, 'id', None), exc)

    return {'status': 'ok', 'notification': serialized}
