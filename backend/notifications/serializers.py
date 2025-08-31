from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Notification

User = get_user_model()


class UserLiteSerializer(serializers.ModelSerializer):
    """Lightweight user serializer used in notification payloads."""
    class Meta:
        model = User
        fields = ('user_id', 'username', 'full_name', 'email', 'contact', 'company_name')


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserLiteSerializer(read_only=True)
    recipient = UserLiteSerializer(read_only=True)
    # recipient_id is write-only and optional for server-side creation
    recipient_id = serializers.CharField(write_only=True, required=False, allow_blank=False)
    verb = serializers.CharField(required=True)

    class Meta:
        model = Notification
        fields = ('id', 'recipient', 'recipient_id', 'actor', 'verb', 'message', 'read', 'created_at')
        read_only_fields = ('actor', 'created_at', 'recipient')

    def validate_recipient_id(self, value):
        """Validate and return a User instance for recipient_id."""
        try:
            user = User.objects.get(user_id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this ID does not exist.")
        return user

    def validate(self, attrs):
        """
        Ensure required fields are present.
        `verb` is already required by the field; this is defensive for better error messages.
        """
        if 'verb' not in attrs or not attrs.get('verb'):
            raise serializers.ValidationError({"verb": "This field is required."})
        # allow creation by server tasks without recipient_id (they can pass a User instance to create())
        return attrs

    def create(self, validated_data):
        """
        Create a Notification.
        `recipient_id` validator returns a User instance (we keep name 'recipient_id' for API compatibility).
        Actor will default to request.user if present in serializer context.
        """
        recipient = None
        # If validate_recipient_id ran, validated_data['recipient_id'] is a User instance
        if 'recipient_id' in validated_data:
            recipient = validated_data.pop('recipient_id')
            # defensive: if it's a string, resolve it
            if isinstance(recipient, str):
                recipient = User.objects.get(user_id=recipient)

        actor = None
        request = self.context.get('request') if self.context else None
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            actor = request.user

        # If someone passed a 'recipient' object directly (rare), prefer it
        recipient = recipient or validated_data.pop('recipient', None)

        if recipient is None:
            raise serializers.ValidationError({"recipient_id": "Recipient must be provided."})

        notification = Notification.objects.create(
            recipient=recipient,
            actor=actor,
            **validated_data
        )
        return notification
