from django.contrib import admin
from .models import ConnectionRequest, Connection

@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ('id','from_user','to_user','status','created_at','responded_at')
    list_filter = ('status',)
    search_fields = ('from_user__username','to_user__username','from_user__email','to_user__email')

@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ('id','user1','user2','connected_at')
    search_fields = ('user1__username','user2__username','user1__email','user2__email')
