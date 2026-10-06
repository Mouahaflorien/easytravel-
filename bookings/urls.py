from django.urls import path
from . import views

app_name = 'bookings'
urlpatterns = [
    path('depart/<int:departure_id>/', views.book_departure, name='book'),
    path('confirmation/<str:reference>/', views.booking_confirmation, name='confirmation'),
    path('feedback/<str:reference>/', views.booking_feedback_view, name='feedback'),
]
