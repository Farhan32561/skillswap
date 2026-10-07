# Farhan's part
import uuid
from pathlib import Path
from django.conf import settings
from django.db import models
from django.db.models import Avg, Q


def profile_image_path(instance, filename):
    return f'profiles/{instance.user_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, max_length=1000)
    location = models.CharField(max_length=150, blank=True)
    image = models.ImageField(upload_to=profile_image_path, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def completed_exchanges(self):
        from pranay.exchanges.models import ExchangeRequest
        return ExchangeRequest.objects.filter(Q(sender=self.user) | Q(receiver=self.user), status='completed').count()

    @property
    def rating(self):
        value = self.user.reviews_received.aggregate(value=Avg('rating'))['value']
        return round(value, 1) if value is not None else None

    @property
    def review_count(self):
        return self.user.reviews_received.count()

    def __str__(self):
        return self.user.username
