# Pranay's part
from django.apps import AppConfig


class ExchangesConfig(AppConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'
    name = 'pranay.exchanges'
    label = 'exchanges'
