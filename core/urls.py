from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('travel.urls')),
    path('reservation/', include('bookings.urls')),
    path('paiements/', include('payments.urls')),
    path('compte/', include('accounts.urls')),
    path('portail-agence/', include('agencies.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
