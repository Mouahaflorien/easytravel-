from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from . import pwa

urlpatterns = [
    path('admin/', admin.site.urls),
    path('manifest.json', pwa.manifest_view, name='pwa_manifest'),
    path('sw.js', pwa.service_worker_view, name='pwa_service_worker'),
    path('offline/', pwa.offline_view, name='pwa_offline'),
    path('', include('travel.urls')),
    path('reservation/', include('bookings.urls')),
    path('paiements/', include('payments.urls')),
    path('compte/', include('accounts.urls')),
    path('portail-agence/', include('agencies.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
