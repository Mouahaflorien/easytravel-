import logging
import traceback
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import Booking
from accounts.models import SystemAlert
from accounts.services.email_service import (
    send_trip_reminder_email, 
    send_satisfaction_survey_email,
    send_missed_trip_email
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envoie les emails automatisés (rappels 24h avant, sondages et relances 2h après)'

    def handle(self, *args, **kwargs):
        now = timezone.localtime()
        self.stdout.write(f"Démarrage des envois automatiques à {now}")

        try:
            # 1. Rappels (24 heures avant le départ)
            target_time_reminder_start = now + timedelta(hours=23)
            target_time_reminder_end = now + timedelta(hours=24)
            
            reminders = Booking.objects.filter(
                status='confirmed',
                traveler_email__isnull=False,
                departure__date=target_time_reminder_end.date(),
                departure__time__gte=target_time_reminder_start.time(),
                departure__time__lte=target_time_reminder_end.time()
            ).select_related('departure', 'departure__agency', 'departure_stop__city', 'arrival_stop__city')
            
            reminder_count = 0
            for booking in reminders:
                if send_trip_reminder_email(booking):
                    reminder_count += 1
                    
            self.stdout.write(f"{reminder_count} rappel(s) envoyé(s).")

            # 2. Post-Voyage (2 heures après le départ estimé)
            target_time_post_start = now - timedelta(hours=3)
            target_time_post_end = now - timedelta(hours=2)
            
            post_trip_bookings = Booking.objects.filter(
                status__in=['confirmed', 'boarded'],
                traveler_email__isnull=False,
                departure__date=target_time_post_end.date(),
                departure__time__gte=target_time_post_start.time(),
                departure__time__lte=target_time_post_end.time()
            ).select_related('departure', 'departure__agency', 'departure_stop__city', 'arrival_stop__city')
            
            survey_count = 0
            missed_count = 0
            
            for booking in post_trip_bookings:
                if booking.status == 'boarded':
                    if not hasattr(booking, 'feedback'):
                        if send_satisfaction_survey_email(None, booking):
                            survey_count += 1
                elif booking.status == 'confirmed':
                    if send_missed_trip_email(booking):
                        missed_count += 1
                        
            self.stdout.write(f"{survey_count} sondage(s) envoyé(s).")
            self.stdout.write(f"{missed_count} email(s) de voyage manqué envoyé(s).")
            self.stdout.write(self.style.SUCCESS('Terminé.'))
            
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Erreur CRITIQUE dans send_automated_emails: {e}")
            SystemAlert.objects.create(
                title="Échec de la tâche automatisée d'envoi d'emails",
                message=f"La tâche planifiée 'send_automated_emails' a échoué.\n\nErreur:\n{str(e)}\n\nDétails techniques:\n{error_details}",
                level='error'
            )
            self.stdout.write(self.style.ERROR('Échec de la tâche avec erreur.'))
