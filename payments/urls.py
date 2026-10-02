"""
URL patterns for EasyTravel Payments.
"""

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('payer/<int:booking_id>/', views.initiate_booking_payment, name='initiate'),
    path('simulation/<int:booking_id>/', views.simulation_checkout, name='simulation_checkout'),
    path('simulation/<int:booking_id>/process/', views.simulation_process, name='simulation_process'),
    path('cinetpay/notification/', views.cinetpay_notification, name='notification'),
    path('cinetpay/retour/', views.cinetpay_return, name='return'),
]

