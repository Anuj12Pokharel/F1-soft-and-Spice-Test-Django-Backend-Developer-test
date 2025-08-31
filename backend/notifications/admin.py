from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'actor', 'verb', 'read', 'created_at')
    list_filter = ('read',)
    search_fields = ('recipient__username', 'actor__username', 'verb', 'message')
