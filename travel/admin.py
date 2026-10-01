from django.contrib import admin
from .models import City, Line, LineStop, Vehicle, Departure

admin.site.register(City)
admin.site.register(Line)
admin.site.register(LineStop)
admin.site.register(Vehicle)
admin.site.register(Departure)
 
