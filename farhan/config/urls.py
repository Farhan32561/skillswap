# Farhan's part
from django.contrib import admin
from django.urls import include, path, register_converter
from django.conf import settings
from django.conf.urls.static import static
from .converters import ObjectIdConverter
from .views import home

register_converter(ObjectIdConverter, "objectid")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('accounts/', include('farhan.accounts.urls')),
    path('skills/', include('ankon.skills.urls')),
    path('exchanges/', include('pranay.exchanges.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
