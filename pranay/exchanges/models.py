# Pranay's part
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class ExchangeRequest(models.Model):
    STATUSES = [(value, value.title()) for value in ('pending', 'accepted', 'rejected', 'cancelled', 'completed')]
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exchanges_sent')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exchanges_received')
    sender_skill = models.ForeignKey('skills.Skill', on_delete=models.PROTECT, related_name='sender_exchanges')
    receiver_skill = models.ForeignKey('skills.Skill', on_delete=models.PROTECT, related_name='receiver_exchanges')
    message = models.TextField(blank=True, max_length=2000)
    status = models.CharField(max_length=20, choices=STATUSES, default='pending', db_index=True)
    # One active exchange per pair in either direction. MongoDB unique indexes
    # treat nulls as distinct, permitting multiple completed/rejected exchanges.
    active_key = models.CharField(max_length=49, unique=True, null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', 'pk']

    @staticmethod
    def pair_key(first, second):
        return ':'.join(sorted((str(first), str(second))))

    def clean(self):
        super().clean()
        if self.sender_id and self.sender_id == self.receiver_id:
            raise ValidationError('You cannot send an exchange request to yourself.')

    def save(self, *args, **kwargs):
        self.active_key = self.pair_key(self.sender_id, self.receiver_id) if self.status in ('pending', 'accepted') else None
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.sender} → {self.receiver}: {self.status}'


class Review(models.Model):
    exchange = models.ForeignKey(ExchangeRequest, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_written')
    reviewed_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', 'pk']
        constraints = [models.UniqueConstraint(fields=['exchange', 'reviewer'], name='one_review_per_participant')]

    def clean(self):
        super().clean()
        if not self.exchange_id or not self.reviewer_id or not self.reviewed_user_id:
            return
        participants = {self.exchange.sender_id, self.exchange.receiver_id}
        if self.exchange.status != 'completed':
            raise ValidationError('Only completed exchanges can be reviewed.')
        if self.reviewer_id not in participants or self.reviewed_user_id not in participants:
            raise ValidationError('Only exchange participants can review their partner.')
        if self.reviewer_id == self.reviewed_user_id:
            raise ValidationError('You cannot review yourself.')

    def __str__(self):
        return f'{self.reviewer}: {self.rating}/5'
