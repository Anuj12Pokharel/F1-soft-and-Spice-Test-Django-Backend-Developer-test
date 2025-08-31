from rest_framework import permissions

class IsRecipientOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow the notification recipient to edit/delete it.
    - SAFE_METHODS (GET, HEAD, OPTIONS) are allowed for any authenticated user (list/retrieve
      is also constrained by get_queryset in the view).
    - For unsafe methods (POST, PUT, PATCH, DELETE) the request.user must be the recipient.
    """
    def has_permission(self, request, view):
        # Require authentication for all notification operations
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        # Otherwise only the recipient can modify/delete
        return obj.recipient == request.user


class IsStaffOrSystemCreateOnly(permissions.BasePermission):
    """
    Allow creation of notifications via API only for staff/superuser accounts.
    (In normal operation notifications should be created by server-side tasks, not by public clients.)
    - If you want to allow an internal service or admin panel to create notifications, make them staff.
    - Celery tasks that create Notification objects directly in DB are unaffected because they don't use this API permission.
    """
    def has_permission(self, request, view):
        if request.method != 'POST':
            return True
        # Only staff/superuser may create via the API.
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


class IsRecipientOrActorOrReadOnly(permissions.BasePermission):
    """
    Variant: allows recipient OR actor to perform updates (useful if you let the actor mark
    some state). Use only if you want actors to be able to modify notifications.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (obj.recipient == request.user) or (obj.actor == request.user)
