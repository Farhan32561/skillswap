# Farhan's part
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'
    name = 'farhan.accounts'
    label = 'accounts'

    def ready(self):
        from . import signals, checks  # noqa: F401
