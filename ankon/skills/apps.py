# Ankon's part
from django.apps import AppConfig


class SkillsConfig(AppConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'
    name = 'ankon.skills'
    label = 'skills'
