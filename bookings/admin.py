from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'traveler_name', 'id_type', 'id_number', 'traveler_phone', 'departure', 'seats_reserved', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'id_type', 'departure__agency', 'created_at')
    search_fields = ('reference', 'traveler_name', 'traveler_phone', 'id_number', 'traveler_email')
