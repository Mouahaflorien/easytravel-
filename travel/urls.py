from django.urls import path
from . import views

app_name = 'travel'
urlpatterns = [
    path('', views.home, name='home'),
    path('recherche/', views.search, name='search'),
]
