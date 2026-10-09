from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'agencies'
urlpatterns = [
    path('login/', views.AgencyLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='agencies:login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    

    # Lines (Trajets)
    path('trajets/', views.LineListView.as_view(), name='line_list'),
    path('trajets/<int:pk>/modifier/', views.LineUpdateView.as_view(), name='line_update'),
    
    # Vehicles
    path('vehicules/', views.VehicleListView.as_view(), name='vehicle_list'),
    path('vehicules/nouveau/', views.VehicleCreateView.as_view(), name='vehicle_create'),
    path('vehicules/<int:pk>/modifier/', views.VehicleUpdateView.as_view(), name='vehicle_update'),
    path('vehicules/<int:pk>/supprimer/', views.VehicleDeleteView.as_view(), name='vehicle_delete'),
    
    # Departures
    path('departs/', views.DepartureListView.as_view(), name='departure_list'),
    path('departs/nouveau/', views.DepartureCreateView.as_view(), name='departure_create'),
    path('departs/<int:pk>/modifier/', views.DepartureUpdateView.as_view(), name='departure_update'),
    path('departs/<int:pk>/supprimer/', views.DepartureDeleteView.as_view(), name='departure_delete'),
    path('departs/<int:pk>/annuler/', views.departure_cancel, name='departure_cancel'),
    
    # Bookings
    path('reservations/', views.BookingListView.as_view(), name='booking_list'),
    path('reservations/nouvelle/', views.agency_booking_create, name='booking_create'),
    path('reservations/<int:booking_id>/statut/', views.update_booking_status, name='update_booking_status'),
    path('reservations/<int:booking_id>/rappel/', views.send_booking_reminder, name='send_booking_reminder'),
    path('reservations/scan/', views.ajax_scan_ticket, name='ajax_scan_ticket'),
    path('departs/<int:departure_id>/manifeste/', views.departure_manifest, name='departure_manifest'),
    path('departs/<int:departure_id>/passagers/', views.departure_manifest, name='departure_passengers'),
    
    # Agency Settings (Affichage, Légal, Opérationnel, Matériel, Notifications)
    path('parametres/', views.agency_settings, name='settings'),
    
    # Centre de Traitement des Anomalies & Sentinelle IA Gemini ("Il signale, un humain tranche")
    path('anomalies/', views.anomaly_list, name='anomaly_list'),
    path('anomalies/<int:pk>/', views.anomaly_detail, name='anomaly_detail'),
    path('anomalies/<int:pk>/trancher/', views.anomaly_arbitrate, name='anomaly_arbitrate'),
    path('anomalies/lancer-audit/', views.anomaly_run_audit, name='anomaly_run_audit'),
    
    # Notifications & Alertes
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/marquer-lues/', views.mark_notifications_read, name='mark_notifications_read'),

    # Multi-Agency Switching
    path('changer-agence/<int:agency_id>/', views.switch_agency, name='switch_agency'),
]


