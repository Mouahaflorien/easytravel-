from django.contrib import admin
from .models import Booking, BookingFeedback

@admin.register(BookingFeedback)
class BookingFeedbackAdmin(admin.ModelAdmin):
    list_display = ('booking', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('booking__reference', 'comment')
    readonly_fields = ('booking', 'rating', 'comment', 'created_at')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'traveler_name', 'traveler_phone', 'departure', 'seats_reserved', 'status', 'created_at')
    list_filter = ('status', 'payment_status', 'id_type', 'departure__agency', 'created_at')
    list_select_related = ('departure', 'departure__agency', 'user')
    raw_id_fields = ('user', 'departure', 'departure_stop', 'arrival_stop')
    search_fields = ('reference', 'traveler_name', 'traveler_phone', 'id_number', 'traveler_email')
    
    # Rendre la référence et les logs de paiement impossibles à modifier
    readonly_fields = ('reference', 'created_at', 'transaction_id', 'paid_at')

    fieldsets = (
        ('Identifiants Réservation', {
            'fields': ('reference', 'status', 'payment_status', 'transaction_id', 'payment_method')
        }),
        ('Informations Passager (Modifiables)', {
            'fields': ('traveler_name', 'traveler_phone', 'traveler_email', 'id_type', 'id_number')
        }),
        ('Détails du Voyage', {
            'fields': ('user', 'departure', 'seats_reserved', 'total_amount', 'departure_stop', 'arrival_stop')
        }),
        ('Dates', {
            'fields': ('created_at', 'paid_at')
        }),
    )
    
    actions = ['send_reminders', 'send_survey', 'cancel_and_refund', 'send_ticket_email']

    @admin.action(description="Envoyer l'e-mail de confirmation (Billet) au(x) passager(s)")
    def send_ticket_email(self, request, queryset):
        from accounts.services.email_service import send_ticket_confirmation_email
        count_success = 0
        count_failed = 0
        
        for booking in queryset:
            if booking.traveler_email and booking.payment_status == 'paid':
                if send_ticket_confirmation_email(request, booking):
                    count_success += 1
                else:
                    count_failed += 1
            else:
                count_failed += 1
                
        if count_success > 0:
            self.message_user(request, f"{count_success} e-mail(s) de billet(s) envoyé(s) avec succès.", level='SUCCESS')
        if count_failed > 0:
            self.message_user(request, f"{count_failed} réservation(s) ignorée(s) (pas d'e-mail ou non payée/SMTP non configuré).", level='WARNING')

    @admin.action(description="Annuler la réservation et créditer le portefeuille du client")
    def cancel_and_refund(self, request, queryset):
        from django.db import transaction
        from accounts.services.email_service import send_cancellation_email
        count_success = 0
        count_failed = 0
        
        for booking in queryset:
            if booking.status != 'cancelled':
                with transaction.atomic():
                    # Libérer les places de façon atomique
                    if booking.cancel():
                        # Créditer l'utilisateur
                        if hasattr(booking.user, 'wallet_balance'):
                            booking.user.wallet_balance += booking.total_amount
                            booking.user.save(update_fields=['wallet_balance'])
                            
                        # Mettre à jour le statut du paiement (status est déjà mis à jour par cancel())
                        booking.payment_status = 'refunded'
                        booking.save(update_fields=['payment_status'])
                    
                # Envoyer l'email d'annulation
                send_cancellation_email(booking)
                count_success += 1
            else:
                count_failed += 1
                
        if count_success > 0:
            self.message_user(request, f"{count_success} réservation(s) annulée(s) avec remboursement.", level='SUCCESS')
        if count_failed > 0:
            self.message_user(request, f"{count_failed} réservation(s) ignorée(s) car déjà annulée(s).", level='WARNING')

    @admin.action(description="Envoyer un e-mail de rappel aux passagers sélectionnés")
    def send_reminders(self, request, queryset):
        from accounts.services.email_service import send_trip_reminder_email
        count_success = 0
        count_failed = 0
        
        for booking in queryset:
            if booking.traveler_email and booking.status != 'cancelled':
                if send_trip_reminder_email(booking):
                    count_success += 1
                else:
                    count_failed += 1
            else:
                count_failed += 1
                
        if count_success > 0:
            self.message_user(request, f"{count_success} rappel(s) envoyé(s) avec succès.", level='SUCCESS')
        if count_failed > 0:
            self.message_user(request, f"{count_failed} réservation(s) ignorée(s) (pas d'e-mail ou billet annulé).", level='WARNING')
            
    @admin.action(description="Envoyer une enquête de satisfaction aux passagers sélectionnés")
    def send_survey(self, request, queryset):
        from accounts.services.email_service import send_satisfaction_survey_email
        count_success = 0
        count_failed = 0
        
        for booking in queryset:
            # On envoie seulement à ceux qui ont une adresse email et dont le billet a été validé ou embarqué
            if booking.traveler_email and booking.status in ['confirmed', 'boarded']:
                if send_satisfaction_survey_email(request, booking):
                    count_success += 1
                else:
                    count_failed += 1
            else:
                count_failed += 1
                
        if count_success > 0:
            self.message_user(request, f"{count_success} enquête(s) de satisfaction envoyée(s).", level='SUCCESS')
        if count_failed > 0:
            self.message_user(request, f"{count_failed} réservation(s) ignorée(s) (pas d'e-mail ou statut invalide).", level='WARNING')

