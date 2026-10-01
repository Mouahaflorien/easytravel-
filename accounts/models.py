from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('manager', "Responsable d'agence"),
        ('agent', "Agent d'agence"),
        ('traveler', 'Voyageur'),
    )
    ID_TYPE_CHOICES = (
        ('CNI', "Carte Nationale d'Identité (CNI)"),
        ('PASSPORT', "Passeport"),
        ('RECEIPT', "Récépissé de CNI"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='traveler')
    phone = models.CharField(max_length=25, blank=True)
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES, default='CNI', blank=True)
    id_number = models.CharField(max_length=50, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    def __str__(self):
        return self.username
