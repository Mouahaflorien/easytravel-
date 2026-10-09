from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Agency
from .importer import import_agency_data

@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'created_at')
    list_filter = ('status', 'theme_mode')
    search_fields = ('name', 'owner__username')
    
    fieldsets = (
        ('Identité de l\'Agence', {
            'fields': ('name', 'legal_name', 'owner', 'status', 'logo', 'license_number', 'tax_id')
        }),
        ('Design & Marque Blanche (Application)', {
            'description': 'Personnalisez les couleurs et le style visuel de l\'espace de réservation (B2C) pour cette agence.',
            'fields': ('primary_color', 'theme_mode', 'language')
        }),
        ('Paramètres de Réservation & Paiement', {
            'fields': ('currency', 'vat_rate', 'timezone', 'booking_cutoff_minutes', 'cancellation_deadline_hours', 'platform_fee_percentage')
        }),
        ('Paramètres des Billets (PDF & Guichet)', {
            'description': 'Ces textes apparaîtront en bas des billets imprimés ou PDF.',
            'fields': ('ticket_terms', 'printer_format', 'date_format', 'time_format')
        }),
        ('Matériel & Notifications', {
            'fields': ('scanner_enabled', 'scale_enabled', 'notify_sms_booking', 'notify_sms_reminder', 'notify_email_ticket', 'notify_agent_sound')
        }),
        ('Coordonnées & Support', {
            'fields': ('phone', 'whatsapp', 'email', 'address')
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:agency_id>/import-csv/', self.admin_site.admin_view(self.import_csv), name='agency-import-csv'),
            path('<int:agency_id>/smart-import/', self.admin_site.admin_view(self.smart_import), name='agency-smart-import'),
        ]
        return custom_urls + urls

    def smart_import(self, request, agency_id):
        from agencies.services.gemini_smart_importer import GeminiSmartImporter
        agency = self.get_object(request, agency_id)
        
        if request.method == "POST":
            raw_text = request.POST.get("raw_text", "").strip()
            uploaded_file = request.FILES.get("upload_file")
            
            # Extraction du texte depuis le fichier s'il est fourni
            if uploaded_file:
                try:
                    raw_text += "\n" + uploaded_file.read().decode('utf-8')
                except Exception as e:
                    messages.error(request, "Erreur de lecture du fichier. Assurez-vous que c'est un fichier texte lisible (TXT, CSV).")
                    return redirect(request.path)
                    
            if not raw_text:
                messages.error(request, "Veuillez fournir du texte ou un fichier à analyser.")
            else:
                try:
                    importer = GeminiSmartImporter(agency)
                    stats = importer.extract_and_import(raw_text)
                    messages.success(request, f"✨ Import IA réussi ! Données extraites : {stats['drivers']} chauffeurs, {stats['vehicles']} véhicules, {stats['cities']} villes, {stats['lines']} lignes, {stats['departures']} départs.")
                    return redirect("..")
                except Exception as e:
                    messages.error(request, f"Échec de l'import intelligent : {str(e)}")
        
        context = dict(
            self.admin_site.each_context(request),
            agency=agency,
            title=f"Import Intelligent (Gemini IA) pour {agency.name}"
        )
        return render(request, "admin/agencies/agency/smart_import.html", context)

    def import_csv(self, request, agency_id):
        agency = self.get_object(request, agency_id)
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file or not csv_file.name.endswith('.csv'):
                messages.error(request, "Veuillez fournir un fichier CSV valide.")
            elif csv_file.size > 2 * 1024 * 1024: # 2 Mo max
                messages.error(request, "Le fichier est trop volumineux. La taille maximale est de 2 Mo.")
            else:
                try:
                    import_agency_data(agency, csv_file)
                    messages.success(request, "Données importées avec succès !")
                    return redirect("..")
                except Exception as e:
                    messages.error(request, f"Erreur lors de l'import : {str(e)}")
        
        context = dict(
            self.admin_site.each_context(request),
            agency=agency,
            title=f"Importer des données pour {agency.name}"
        )
        return render(request, "admin/agencies/agency/import_csv.html", context)
