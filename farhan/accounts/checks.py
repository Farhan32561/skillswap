# Farhan's part
from django.conf import settings
from django.core.checks import Warning, register


@register()
def mongodb_configuration(app_configs, **kwargs):
    if not settings.MONGODB_CONFIGURED:
        return [Warning('MONGODB_URI is not configured; database operations require your Atlas URI.',
                        hint='Edit .env, then run python manage.py migrate.', id='skillswap.W001')]
    return []
