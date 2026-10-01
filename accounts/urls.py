from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('connexion/', views.traveler_login, name='login'),
    path('inscription/', views.traveler_register, name='register'),
    path('activation-en-attente/', views.activation_pending, name='activation_pending'),
    path('activer/<str:uidb64>/<str:token>/', views.activate_account, name='activate_account'),
    path('renvoyer-activation/', views.resend_activation, name='resend_activation'),
    path('deconnexion/', views.traveler_logout, name='logout'),
    path('mes-reservations/', views.my_bookings, name='my_bookings'),
]

