# notifications/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer that subscribes the connected user to a per-user group
    named `user_<user_id>`. Expects scope['user'] to be set (either by session
    auth via AuthMiddlewareStack or by custom TokenAuthMiddleware below).
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or getattr(user, "is_anonymous", True):
            # deny connection for unauthenticated users
            await self.close(code=4401)  # 4401 = custom "unauthenticated" code
            return

        # Use stable group name. Use user.user_id if you have a custom identifier,
        # otherwise fall back to user.pk.
        user_key = getattr(user, "user_id", None) or getattr(user, "pk", None)
        self.group_name = f"user_{user_key}"

        # Register to group and accept connection
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.debug("WS connect: user=%s joined group=%s", user_key, self.group_name)

    async def disconnect(self, close_code):
        # Remove from group on disconnect
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            # if group_name not set or layer failure, ignore
            logger.exception("Error discarding group on disconnect for %s", getattr(self, "group_name", None))

    async def receive_json(self, content, **kwargs):
        """
        Optionally handle incoming JSON from client.
        We'll support a simple 'ping' message so the client can keep the connection alive.
        """
        typ = content.get("type")
        if typ == "ping":
            await self.send_json({"type": "pong"})
            return

        # you can extend this to handle client actions (e.g., mark-read via WS)
        logger.debug("WS received message: %s", content)

    async def notification_message(self, event):
        """
        Handler for group messages sent via channel_layer.group_send.
        Event shape should include a 'notification' key with serializable payload.
        """
        notification = event.get("notification")
        if not notification:
            # nothing to send
            return
        # ensure the payload is JSON-serializable
        await self.send_json({"type": "notification", "data": notification})
