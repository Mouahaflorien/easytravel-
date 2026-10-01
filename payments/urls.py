"""
URL patterns for EasyTravel Payments.
"""

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('payer/<int:booking_id>/', views.initiate_booking_payment, name='initiate'),
    path('cinetpay/notification/', views.cinetpay_notification, name='notification'),
    path('cinetpay/retour/', views.cinetpay_return, name='return'),
]
