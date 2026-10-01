from django.db import models
from django.conf import settings

class Agency(models.Model):
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('active', 'Active'),
        ('suspended', 'Suspendue'),
        ('rejected', 'Refusée'),
    )
    THEME_CHOICES = (
        ('light', 'Mode Clair'),
        ('dark', 'Mode Sombre'),
        ('system', 'Synchronisé avec le système'),
    )
    LANG_CHOICES = (
        ('fr', 'Français'),
        ('en', 'English'),
        ('de', 'Deutsch'),
    )
    DATE_FORMAT_CHOICES = (
        ('d/m/Y', 'JJ/MM/AAAA'),
        ('Y-m-d', 'AAAA-MM-JJ'),
    )
    TIME_FORMAT_CHOICES = (
        ('24h', '24 Heures (14:30)'),
        ('12h', '12 Heures AM/PM (02:30 PM)'),
    )
    PRINTER_CHOICES = (
        ('a4', 'Standard A4 (Factures & Billets complets)'),
        ('thermal_80', 'Thermique 80mm (Guichet POS Standard)'),
        ('thermal_58', 'Thermique 58mm (Guichet POS Compact)'),
    )

    # 1. Base Identité & Propriétaire
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='agency_logos/', blank=True, null=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agencies_owned')
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    # 2. Profil & Informations Légales (Entreprise)
    legal_name = models.CharField(max_length=150, blank=True, default="", help_text="Raison sociale officielle")
    tax_id = models.CharField(max_length=50, blank=True, default="", help_text="Numéro d'Identifiant Fiscal Unique / RCCM")
    license_number = models.CharField(max_length=100, blank=True, default="N° MINT-TRANS-CMR/2024-AGY", help_text="Agrément ministériel de transport")
    ticket_terms = models.TextField(
        blank=True, 
        default="1. Présentation obligatoire de la CNI/Passeport physique à l'embarquement.\n"
                "2. Présence requise au quai 30 minutes avant l'heure de départ.\n"
                "3. Franchise bagage : 30 kg par passager. Tout excédent est soumis à taxation.\n"
                "4. Billet modifiable jusqu'à 2h avant le départ, non remboursable après départ.",
        help_text="Conditions générales et mentions légales imprimées au bas du ticket"
    )

    # 3. Préférences d'Affichage & Charte Graphique (Marque Blanche)
    theme_mode = models.CharField(max_length=20, choices=THEME_CHOICES, default='light')
    primary_color = models.CharField(max_length=20, default='#2563eb', help_text="Code couleur HEX (ex: #2563eb)")
    language = models.CharField(max_length=10, choices=LANG_CHOICES, default='fr')
    date_format = models.CharField(max_length=20, choices=DATE_FORMAT_CHOICES, default='d/m/Y')
    time_format = models.CharField(max_length=10, choices=TIME_FORMAT_CHOICES, default='24h')

    # 4. Paramètres Opérationnels (Métier)
    currency = models.CharField(max_length=10, default='FCFA')
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Taux de TVA applicable en %")
    timezone = models.CharField(max_length=50, default='Africa/Douala')
    booking_cutoff_minutes = models.PositiveIntegerField(default=30, help_text="Clôture des ventes en ligne (minutes avant départ)")
    cancellation_deadline_hours = models.PositiveIntegerField(default=2, help_text="Délai maximum d'annulation (heures avant départ)")

    # 5. Matériel et Périphériques
    printer_format = models.CharField(max_length=20, choices=PRINTER_CHOICES, default='a4')
    scanner_enabled = models.BooleanField(default=True, help_text="Activer la détection automatique du lecteur de QR code / douchette")
    scale_enabled = models.BooleanField(default=False, help_text="Connexion d'une balance connectée pour la pesée des bagages")

    # 6. Notifications & Automatisations
    notify_sms_booking = models.BooleanField(default=True, help_text="SMS immédiat de confirmation au voyageur")
    notify_sms_reminder = models.BooleanField(default=True, help_text="SMS de rappel 2h avant le départ")
    notify_email_ticket = models.BooleanField(default=True, help_text="Envoi du billet électronique par email")
    notify_agent_sound = models.BooleanField(default=True, help_text="Alerte sonore au guichet lors d'une nouvelle réservation")

    def __str__(self):
        return self.name


class AuditAnomaly(models.Model):
    CATEGORY_CHOICES = (
        ('id_collision', 'Usurpation / Même CNI sous plusieurs identités'),
        ('cashier_cancellation', "Taux d'annulation anormal (Suspicion Caissier)"),
        ('price_mismatch', 'Tarif hors grille officielle'),
        ('unpaid_boarding', 'Passager embarqué sans paiement validé'),
        ('cash_register', 'Écart de réconciliation caisse / billets'),
        ('bogus_identity', 'Identité ou numéro manifestement fictif'),
        ('suspicious_pattern', 'Comportement suspect détecté par IA'),
    )

    SEVERITY_CHOICES = (
        ('critical', 'Critique'),
        ('high', 'Élevée'),
        ('medium', 'Moyenne'),
        ('low', 'Faible'),
    )

    STATUS_CHOICES = (
        ('pending', "En attente d'arbitrage"),
        ('confirmed', 'Fraude / Incohérence confirmée'),
        ('dismissed', 'Classée sans suite (Fausse alerte)'),
        ('regularized', 'Régularisée'),
    )

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='anomalies')
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    title = models.CharField(max_length=255)
    description = models.TextField(help_text="Explication de l'incohérence par Gemini")
    gemini_recommendation = models.TextField(blank=True, default="", help_text="Action recommandée par l'IA")
    
    # Entités associées
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='anomalies')
    departure = models.ForeignKey('travel.Departure', on_delete=models.SET_NULL, null=True, blank=True, related_name='anomalies')
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cashier_anomalies')
    
    # Données brutes et métadonnées
    evidence_data = models.JSONField(default=dict, blank=True, help_text="Données chiffrées / Preuves détectées")
    ai_confidence = models.FloatField(default=0.92, help_text="Indice de confiance de la détection (0 à 1)")
    
    # Arbitrage humain ("Il signale, un humain tranche")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_anomalies')
    resolution_notes = models.TextField(blank=True, default="", help_text="Motif de la décision humaine")
    action_taken = models.CharField(max_length=150, blank=True, default="", help_text="Action effectuée lors du traitement")

    class Meta:
        ordering = ['-detected_at']
        verbose_name = "Anomalie d'Audit Gemini"
        verbose_name_plural = "Anomalies d'Audit Gemini"

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title} ({self.agency.name})"


class AgencyNotification(models.Model):
    LEVEL_CHOICES = (
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('danger', 'Urgent / Critique'),
    )
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='notifications')
    anomaly = models.ForeignKey(AuditAnomaly, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='warning')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification Agence"
        verbose_name_plural = "Notifications Agence"

    def __str__(self):
        return f"Notification {self.title} - {self.agency.name}"


