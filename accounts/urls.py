from django.urls import path
from django.contrib.auth import views as auth_views
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

    # Password Reset
    path('mot-de-passe-oublie/', auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html', success_url='/compte/mot-de-passe-oublie/envoye/'), name='password_reset'),
    path('mot-de-passe-oublie/envoye/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('mot-de-passe-oublie/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html', success_url='/compte/mot-de-passe-oublie/termine/'), name='password_reset_confirm'),
    path('mot-de-passe-oublie/termine/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
]

