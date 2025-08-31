from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, BaseUserManager
)
from django.utils import timezone
import secrets

def generate_unique_user_id():
    return f"SPC-{timezone.now().strftime('%Y%m%d')}-{secrets.token_hex(3)}"

class AppUserManager(BaseUserManager):
    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError('The username must be set')
        if not email:
            raise ValueError('The email must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not password:
            raise ValueError('Superusers must have a password.')
        return self._create_user(username, email, password, **extra_fields)

class AppUser(AbstractBaseUser, PermissionsMixin):
    user_id = models.CharField(
        max_length=64, 
        primary_key=True,  # Set as primary key
        editable=False,
        default=generate_unique_user_id
    )
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255, db_index=True)
    contact = models.CharField(max_length=30, unique=True)
    company_name = models.CharField(max_length=255, blank=True, db_index=True)
    address = models.TextField(blank=True, db_index=True)
    industry = models.CharField(max_length=255, blank=True, db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = AppUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name', 'contact']

    def save(self, *args, **kwargs):
        # If primary key is not set (for new instances)
        if not self.user_id:
            self.user_id = generate_unique_user_id()
            # Ensure uniqueness (very unlikely but possible)
            while AppUser.objects.filter(user_id=self.user_id).exists():
                self.user_id = generate_unique_user_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.user_id})"

    class Meta:
        # if you are *moving* from registration app and want to reuse the old DB table
        # set db_table = 'registration_appuser' (see migration notes below).
        db_table= 'registered_users'
        managed = True
        pass