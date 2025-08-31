from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ConnectionRequest, Connection
from notifications.serializers import NotificationSerializer as _NotificationSerializer
import re

User = get_user_model()

class UserLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('user_id', 'username', 'full_name', 'email', 'contact', 'company_name')

# serializers.py
class ConnectionRequestSerializer(serializers.ModelSerializer):
    from_user = UserLiteSerializer(read_only=True)
    to_user = UserLiteSerializer(read_only=True)
    to_user_id = serializers.CharField(write_only=True)

    class Meta:
        model = ConnectionRequest
        fields = ('id', 'from_user', 'to_user', 'to_user_id', 'message', 'status', 'created_at', 'responded_at')
        read_only_fields = ('status', 'created_at', 'responded_at')

    def validate_to_user_id(self, value):
        """
        Validate that to_user_id is a valid user ID and exists
        """
        # Handle case where frontend might send ["user_id"] instead of "user_id"
        if isinstance(value, list):
            if len(value) == 0:
                raise serializers.ValidationError("User ID cannot be empty.")
            value = value[0]  # Take the first element
        
        # Validate the user ID format
        pattern = r'^SPC-\d{8}-[a-f0-9]{6}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError("Invalid user ID format.")
        
        # Check if the user exists
        try:
            user = User.objects.get(user_id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this ID does not exist.")
        
        return user  # Return the User object, not just the ID

    def validate(self, data):
        request = self.context.get('request')
        from_user = request.user
        to_user = data.get('to_user_id')  # This is now a User object from validate_to_user_id
        
        if to_user == from_user:
            raise serializers.ValidationError("Cannot send request to yourself.")
        
        # Check if pending request already exists
        if ConnectionRequest.objects.filter(
            from_user=from_user, 
            to_user=to_user, 
            status=ConnectionRequest.STATUS_PENDING
        ).exists():
            raise serializers.ValidationError("A pending request already exists.")
        
        # Check if connection already exists
        from django.db.models import Q
        if Connection.objects.filter(
            (Q(user1=from_user) & Q(user2=to_user)) | 
            (Q(user1=to_user) & Q(user2=from_user))
        ).exists():
            raise serializers.ValidationError("You are already connected with this user.")
        
        # Rename to_user_id to to_user for model creation
        data['to_user'] = to_user
        if 'to_user_id' in data:
            del data['to_user_id']
            
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        return ConnectionRequest.objects.create(from_user=request.user, **validated_data)


class ConnectionSerializer(serializers.ModelSerializer):
    user1 = UserLiteSerializer(read_only=True)
    user2 = UserLiteSerializer(read_only=True)

    class Meta:
        model = Connection
        fields = ('id', 'user1', 'user2', 'connected_at')