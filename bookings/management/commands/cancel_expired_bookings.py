from django.core.management.base import BaseCommand
from bookings.models import Booking

class Command(BaseCommand):
    help = "Annule automatiquement les réservations en attente depuis plus de 15 minutes."

    def handle(self, *args, **kwargs):
        count = Booking.cancel_expired_pending_bookings()
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f"{count} réservation(s) annulée(s) avec succès."))
        else:
            self.stdout.write("Aucune réservation à annuler.")
