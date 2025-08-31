from django.urls import path
from .views import RegisterUserAPIView, LoginAPIView, SlidingTokenRefreshView

urlpatterns = [
    path('register/', RegisterUserAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('token/refresh/', SlidingTokenRefreshView.as_view(), name='token_refresh'),
]
