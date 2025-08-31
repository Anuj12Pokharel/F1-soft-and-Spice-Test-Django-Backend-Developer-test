from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ConnectionRequestViewSet, ConnectionViewSet, search_users

router = DefaultRouter()
router.register(r'requests', ConnectionRequestViewSet, basename='connectionrequest')
router.register(r'connections', ConnectionViewSet, basename='connection')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', search_users, name='user-search'),
]
