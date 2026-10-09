import uuid
from django.db import models
from django.conf import settings
from travel.models import Departure, LineStop

class BookingCart(models.Model):
    reference = models.CharField(max_length=15, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, default="")
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"CRT-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('boarded', 'Embarqué(e)'),
        ('cancelled', 'Annulée'),
    )
    ID_TYPE_CHOICES = (
        ('cni', "Carte Nationale d'Identité (CNI)"),
        ('passport', "Passeport"),
        ('school_card', "Carte scolaire"),
        ('other', "Autre"),
        ('none', "Aucune pièce"),
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
    
    cart = models.ForeignKey(BookingCart, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    reference = models.CharField(max_length=15, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    departure = models.ForeignKey(Departure, on_delete=models.CASCADE, related_name='bookings')
    
    # Tronçon réservé
    departure_stop = models.ForeignKey(LineStop, on_delete=models.CASCADE, related_name='departing_bookings', null=True, blank=True)
    arrival_stop = models.ForeignKey(LineStop, on_delete=models.CASCADE, related_name='arriving_bookings', null=True, blank=True)
    
    # Infos Voyageur & Pièce d'identité
    traveler_name = models.CharField(max_length=150, verbose_name="Nom complet du voyageur")
    traveler_phone = models.CharField(max_length=25, verbose_name="Numéro de téléphone camerounais")
    traveler_email = models.EmailField(blank=True, null=True, verbose_name="Adresse email")
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES, default='none', verbose_name="Type de pièce")
    id_number = models.CharField(max_length=50, default="", blank=True, null=True, verbose_name="Numéro de la pièce d'identité")
    
    # Détails Réservation & Encaissement
    seats_reserved = models.PositiveIntegerField(default=1)
    
    # Séparation Financière
    agency_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Montant reversé à l'agence")
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Frais de service EasyTravel")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Montant total payé par le client (Agence + Frais)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name="Statut du paiement")
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True, verbose_name="Mode d'encaissement")
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

    def cancel(self):
        from django.db import transaction
        from travel.models import Departure
        with transaction.atomic():
            b = Booking.objects.select_for_update().get(pk=self.pk)
            if b.status != 'cancelled':
                b.status = 'cancelled'
                if b.departure:
                    dep = Departure.objects.select_for_update().get(pk=b.departure.pk)
                    dep.available_capacity += b.seats_reserved
                    dep.save(update_fields=['available_capacity'])
                b.save(update_fields=['status'])
                self.status = 'cancelled'
                return True
        return False

    @classmethod
    def cancel_expired_pending_bookings(cls):
        from django.utils import timezone
        from django.db import transaction
        from datetime import timedelta
        # On annule les réservations qui sont restées 'pending' plus de 15 minutes
        expiration_time = timezone.now() - timedelta(minutes=15)
        
        with transaction.atomic():
            expired_bookings = list(cls.objects.select_for_update().filter(
                status__in=['pending', 'confirmed'],
                payment_status='pending',
                created_at__lt=expiration_time
            ).select_related('departure'))
            
            count = 0
            for booking in expired_bookings:
                if booking.cancel():
                    booking.payment_status = 'failed'
                    booking.save(update_fields=['payment_status'])
                    count += 1
                
        return count

class BookingFeedback(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='feedback')
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)], help_text="Note sur 5")
    comment = models.TextField(blank=True, help_text="Commentaire du client")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Sondage de satisfaction"
        verbose_name_plural = "Sondages de satisfaction"

    def __str__(self):
        return f"Sondage pour {self.booking.reference} - {self.rating}/5"
