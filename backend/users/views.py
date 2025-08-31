# views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework_simplejwt.tokens import SlidingToken
from django.contrib.auth import login as django_login
from django.contrib.auth import get_user_model
from .serializers import RegistrationSerializer, LoginSerializer, UserDetailSerializer
from .throttles import LoginRateThrottle
from rest_framework_simplejwt.views import TokenRefreshSlidingView

User = get_user_model()


class RegisterUserAPIView(generics.CreateAPIView):
    """
    POST -> create a new user.
    Uses RegistrationSerializer for validation & creation.
    """
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        # Use GenericAPIView helpers
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Use UserDetailSerializer instead of RegistrationSerializer for response
        user_data = UserDetailSerializer(user).data

        return Response(
            {
                "message": "User registered successfully.",
                "user": user_data,
            },
            status=status.HTTP_201_CREATED,
        )

# views.py
class LoginAPIView(GenericAPIView):
    """
    POST -> validate credentials via LoginSerializer, log user in and return sliding token.
    """
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Optional: set session auth if needed
        try:
            django_login(request, user)
        except Exception:
            # ignore session login failures
            pass

        # This should now work with your custom user_id field
        token = SlidingToken.for_user(user)
        token_str = str(token)

        user_data = UserDetailSerializer(user).data

        return Response(
            {
                "message": "Login successful.",
                "token": token_str,
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )

class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    GET, PUT, PATCH -> retrieve or update user profile
    """
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class SlidingTokenRefreshView(TokenRefreshSlidingView):
    permission_classes = [permissions.AllowAny]