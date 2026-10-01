from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Agency
from .importer import import_agency_data

@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'owner__username')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:agency_id>/import-csv/', self.admin_site.admin_view(self.import_csv), name='agency-import-csv'),
        ]
        return custom_urls + urls

    def import_csv(self, request, agency_id):
        agency = self.get_object(request, agency_id)
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file or not csv_file.name.endswith('.csv'):
                messages.error(request, "Veuillez fournir un fichier CSV valide.")
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
