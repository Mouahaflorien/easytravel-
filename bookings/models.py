import uuid
from django.db import models
from django.conf import settings
from travel.models import Departure, LineStop

class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('boarded', 'Embarqué(e)'),
        ('cancelled', 'Annulée'),
    )
    ID_TYPE_CHOICES = (
        ('CNI', "Carte Nationale d'Identité (CNI)"),
        ('PASSPORT', "Passeport"),
        ('RECEIPT', "Récépissé de CNI"),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('paid', 'Payé / Encaissé'),
        ('pending', 'En attente de règlement'),
        ('refunded', 'Remboursé'),
        ('failed', 'Échoué / Non réglé'),
    )
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Espèces (Guichet)'),
        ('orange_money', 'Orange Money'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('card', 'Carte Bancaire'),
        ('online', 'Paiement en ligne'),
    )
    
    reference = models.CharField(max_length=15, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    departure = models.ForeignKey(Departure, on_delete=models.CASCADE, related_name='bookings')
    
    # Tronçon réservé
    departure_stop = models.ForeignKey(LineStop, on_delete=models.CASCADE, related_name='departing_bookings', null=True)
    arrival_stop = models.ForeignKey(LineStop, on_delete=models.CASCADE, related_name='arriving_bookings', null=True)
    
    # Infos Voyageur & Pièce d'identité (Obligatoire selon réglementation)
    traveler_name = models.CharField(max_length=150, verbose_name="Nom complet du voyageur")
    traveler_phone = models.CharField(max_length=25, verbose_name="Numéro de téléphone camerounais")
    traveler_email = models.EmailField(verbose_name="Adresse email")
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES, default='CNI', verbose_name="Type de pièce")
    id_number = models.CharField(max_length=50, default="", verbose_name="Numéro de la pièce d'identité")
    
    # Détails Réservation & Encaissement
    seats_reserved = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='paid', verbose_name="Statut du paiement")
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='cash', verbose_name="Mode d'encaissement")
    transaction_id = models.CharField(max_length=100, blank=True, default="", verbose_name="ID Transaction Passerelle")
    payment_operator = models.CharField(max_length=50, blank=True, default="", verbose_name="Opérateur (MTN, Orange, etc.)")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Date d'encaissement")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.reference:
            # Génération d'une référence courte, pro et unique: ET-XXXXXXXX
            self.reference = f"ET-{str(uuid.uuid4()).upper()[:8]}"
        if self.payment_status == 'paid' and not self.paid_at:
            from django.utils import timezone
            self.paid_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Réservation {self.reference} - {self.traveler_name}"
