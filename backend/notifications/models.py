from django.conf import settings
from django.db import models

# Use settings.AUTH_USER_MODEL to avoid import-time issues
UserModel = settings.AUTH_USER_MODEL

class Notification(models.Model):
    recipient = models.ForeignKey(
        UserModel,
        related_name='notifications',
        on_delete=models.CASCADE,
        # to_field='user_id',  # only if user.user_id is unique; uncomment if so
    )
    actor = models.ForeignKey(
        UserModel,
        related_name='notifications_from',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        # to_field='user_id',  # same note as above
    )
    verb = models.CharField(max_length=100)  # e.g., "accepted your connection request"
    message = models.TextField(blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'Notification'

    def __str__(self):
        return f"Notification to {self.recipient}: {self.verb}"
