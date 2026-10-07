# Ankon's part
from django.conf import settings
from django.db import models
from django.db.models import Q

CATEGORIES = [('programming', 'Programming'), ('design', 'Design'), ('language', 'Language'),
              ('business', 'Business'), ('photography', 'Photography'), ('music', 'Music'), ('other', 'Other')]
LEVELS = [('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced'), ('expert', 'Expert')]


def normalize_name(value):
    return ' '.join(value.split()).casefold()


class SkillCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=100)
    normalized_name = models.CharField(max_length=100, unique=True, editable=False)
    category = models.ForeignKey(SkillCategory, on_delete=models.PROTECT, related_name='skills')
    description = models.TextField(blank=True, max_length=2000)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        self.name = ' '.join(self.name.split())
        self.normalized_name = normalize_name(self.name)
        super().save(*args, **kwargs)

    def get_category_display(self):
        return self.category.name

    def __str__(self):
        return self.name


class SkillMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT)
    experience_level = models.CharField(max_length=20, choices=LEVELS)
    description = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ['-created_at', 'pk']
        constraints = [models.UniqueConstraint(fields=['user', 'skill'], name='%(class)s_user_skill_unique')]

    @property
    def name(self):
        return self.skill.name

    @property
    def owner(self):
        return self.user

    def get_category_display(self):
        return self.skill.category.name

    def get_level_display(self):
        return self.get_experience_level_display()

    @property
    def successful_exchanges(self):
        from pranay.exchanges.models import ExchangeRequest
        return ExchangeRequest.objects.filter(
            Q(sender=self.user, sender_skill=self.skill) | Q(receiver=self.user, receiver_skill=self.skill),
            status='completed',
        ).count()

    def __str__(self):
        return f'{self.user.username}: {self.skill.name}'


class SkillOffer(SkillMembership):
    def get_skill_type_display(self):
        return 'Can Teach'


class SkillWanted(SkillMembership):
    def get_skill_type_display(self):
        return 'Wants to Learn'
