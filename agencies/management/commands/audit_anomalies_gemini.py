from django.core.management.base import BaseCommand
from agencies.models import Agency
from agencies.services.gemini_audit import GeminiAuditService

class Command(BaseCommand):
    help = "Exécute l'audit intelligent Gemini pour détecter les fraudes, comportements suspects et anomalies d'exploitation."

    def add_arguments(self, parser):
        parser.add_argument('--agency', type=int, help="ID spécifique de l'agence à auditer")
        parser.add_argument('--async-mode', action='store_true', help="Exécuter en mode asynchrone (thread d'arrière-plan)")

    def handle(self, *args, **options):
        agency_id = options.get('agency')
        agency = None
        if agency_id:
            try:
                agency = Agency.objects.get(id=agency_id)
                self.stdout.write(self.style.NOTICE(f"Ciblage de l'agence : {agency.name} (ID: {agency.id})"))
            except Agency.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Agence ID {agency_id} introuvable."))
                return

        audit_service = GeminiAuditService(agency=agency)
        self.stdout.write(self.style.NOTICE("Démarrage de l'analyse heuristique et prédictive Gemini..."))

        if options.get('async_mode'):
            audit_service.run_audit_async()
            self.stdout.write(self.style.SUCCESS("Audit lancé en tâche de fond (asynchrone)."))
        else:
            results = audit_service.run_audit_sync()
            self.stdout.write(self.style.SUCCESS(
                f"Audit terminé avec succès ! "
                f"Nouvelles anomalies détectées : {results.get('total_new_anomalies', 0)}"
            ))
