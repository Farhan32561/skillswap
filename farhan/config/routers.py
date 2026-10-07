# Farhan's part
from django.conf import settings


class OfflineMigrationRouter:
    """Let makemigrations build files without trying localhost when URI is absent.

    With a configured URI all migration operations use the normal backend.
    Runtime commands already fail helpfully in settings when URI is missing.
    """

    def allow_migrate(self, db, app_label, **hints):
        return None if settings.MONGODB_CONFIGURED else False
