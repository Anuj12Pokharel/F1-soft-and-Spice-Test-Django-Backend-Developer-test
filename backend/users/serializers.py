from rest_framework import serializers
from django.core.validators import RegexValidator
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError

AppUser = get_user_model()

contact_validator = RegexValidator(
    regex=r'^\+?\d{7,15}$',
    message='Contact number must be 7-15 digits long and may start with +'
)

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    contact = serializers.CharField(validators=[contact_validator])
    email = serializers.EmailField()

    class Meta:
        model = AppUser
        fields = [
            'user_id', 'username', 'email', 'password', 'full_name',
            'contact', 'company_name', 'address', 'industry', 'date_joined'
        ]
        read_only_fields = ['user_id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
            'user_id': {'read_only': True}
        }

    def validate_username(self, value):
        """
        Check that the username is unique (case-insensitive check)
        """
        if AppUser.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_email(self, value):
        """
        Check that the email is unique (case-insensitive check)
        """
        if AppUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def validate_contact(self, value):
        """
        Check that the contact number is unique
        """
        if AppUser.objects.filter(contact=value).exists():
            raise serializers.ValidationError("A user with that contact number already exists.")
        return value

    def create(self, validated_data):
        """
        Create a new user with hashed password and handle integrity errors
        """
        try:
            user = AppUser.objects.create_user(**validated_data)
            return user
        except IntegrityError as e:
            # Handle specific integrity error cases
            error_messages = {
                'username': "Username already exists",
                'email': "Email already exists",
                'contact': "Contact number already exists"
            }
            
            # Check which field caused the integrity error
            for field in ['username', 'email', 'contact']:
                if field in str(e).lower():
                    raise serializers.ValidationError({field: [error_messages[field]]})
            
            # Generic error if specific field not identified
            raise serializers.ValidationError({"detail": "User creation failed due to conflicting information."})

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True, trim_whitespace=False)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            # Authenticate using the custom user model
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError(
                    "Unable to log in with provided credentials.",
                    code='authorization'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    "User account is disabled.",
                    code='authorization'
                )
                
        else:
            raise serializers.ValidationError(
                'Must include "username" and "password".',
                code='authorization'
            )

        attrs['user'] = user
        return attrs

class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for user details (read-only for safe methods)
    """
    class Meta:
        model = AppUser
        fields = [
            'user_id', 'username', 'email', 'full_name',
            'contact', 'company_name', 'address', 'industry',
            'date_joined', 'is_active'
        ]
        read_only_fields = ['user_id', 'date_joined', 'is_active']