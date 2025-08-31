# notifications/token_middleware.py
from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework_simplejwt.tokens import UntypedToken, SlidingToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class QueryStringTokenAuthMiddleware:
    """
    ASGI middleware that checks for a `token` query parameter on WebSocket connect,
    validates the token using SimpleJWT, and sets scope['user'] accordingly.

    Usage:
        application = ProtocolTypeRouter({
            "websocket": QueryStringTokenAuthMiddleware(
                AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
            ),
            ...
        })
    """

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return QueryStringTokenAuthMiddlewareInstance(scope, self.inner)


class QueryStringTokenAuthMiddlewareInstance:
    def __init__(self, scope, inner):
        self.scope = dict(scope)
        self.inner = inner

    async def __call__(self, receive, send):
        query_string = self.scope.get("query_string", b"").decode()
        qs = parse_qs(query_string)
        token = None

        # Prefer 'token' query param; you can also read from headers if you implement that
        if "token" in qs:
            token = qs["token"][0]

        if token:
            try:
                # Validate token signature (will raise on invalid/expired)
                # Using UntypedToken ensures signature and expiration are checked.
                UntypedToken(token)

                # Use SlidingToken to read claims (works for Sliding/JWT tokens)
                sliding = SlidingToken(token)

                # The default user-id claim used by SimpleJWT is "user_id", but check settings
                user_id_claim = getattr(settings, "SIMPLE_JWT", {}).get("USER_ID_CLAIM", "user_id")
                claim_value = sliding.get(user_id_claim) or sliding.get("user_id") or sliding.get("id")

                user = None
                if claim_value is not None:
                    # Try to find by your custom user_id field first, then pk
                    # (This mirrors your project which uses user.user_id)
                    try:
                        user = User.objects.get(user_id=claim_value)
                    except Exception:
                        try:
                            user = User.objects.get(pk=claim_value)
                        except Exception:
                            user = None

                if user:
                    self.scope["user"] = user
                else:
                    logger.debug("Token valid but user not found: claim=%s", claim_value)
                    self.scope["user"] = AnonymousUser()

            except (TokenError, InvalidToken, Exception) as exc:
                logger.debug("Token auth failed for websocket connection: %s", exc)
                self.scope["user"] = AnonymousUser()
        else:
            # No token provided; leave scope['user'] for other middleware (e.g., session auth)
            # If no other auth in stack, set AnonymousUser
            self.scope.setdefault("user", AnonymousUser())

        # Ensure DB connections are fresh for this connection handler
        close_old_connections()
        inner = self.inner(self.scope)
        return await inner(receive, send)
