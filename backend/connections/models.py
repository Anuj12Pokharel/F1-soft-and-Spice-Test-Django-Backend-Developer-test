from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class ConnectionRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    from_user = models.ForeignKey(
        User, 
        related_name='sent_connection_requests', 
        on_delete=models.CASCADE,
        to_field='user_id'  # Specify the custom primary key field
    )
    to_user = models.ForeignKey(
        User, 
        related_name='received_connection_requests', 
        on_delete=models.CASCADE,
        to_field='user_id'  # Specify the custom primary key field
    )
    message = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']
        db_table = 'connections_request'

    def clean(self):
        if self.from_user_id == self.to_user_id:
            raise ValidationError("Cannot send connection request to yourself.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} [{self.status}]"


class Connection(models.Model):
    user1 = models.ForeignKey(
        User, 
        related_name='connections_user1', 
        on_delete=models.CASCADE,
        to_field='user_id'  # Specify the custom primary key field
    )
    user2 = models.ForeignKey(
        User, 
        related_name='connections_user2', 
        on_delete=models.CASCADE,
        to_field='user_id'  # Specify the custom primary key field
    )
    connected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # uniqueness enforced by saving with ordered user1.user_id < user2.user_id
        unique_together = (('user1', 'user2'),)
        ordering = ['-connected_at']
        db_table = 'connections'

    def clean(self):
        if self.user1_id == self.user2_id:
            raise ValidationError("Cannot connect a user to themselves.")

    def save(self, *args, **kwargs):
        # enforce ordering to avoid duplicate symmetric connections
        if self.user1_id and self.user2_id and self.user1_id > self.user2_id:
            self.user1, self.user2 = self.user2, self.user1
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user1} <> {self.user2}"