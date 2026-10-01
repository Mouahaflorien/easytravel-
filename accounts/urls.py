from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('connexion/', views.traveler_login, name='login'),
    path('inscription/', views.traveler_register, name='register'),
    path('deconnexion/', views.traveler_logout, name='logout'),
    path('mes-reservations/', views.my_bookings, name='my_bookings'),
]
