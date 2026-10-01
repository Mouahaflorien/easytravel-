from django import forms
from .models import Agency
from travel.models import Vehicle, Departure, Driver, Line
from bookings.models import Booking

class AgencySettingsForm(forms.ModelForm):
    class Meta:
        model = Agency
        fields = [
            # 1. Affichage & Interface
            'theme_mode', 'primary_color', 'language', 'date_format', 'time_format',
            # 2. Profil & Légal
            'name', 'legal_name', 'logo', 'tax_id', 'license_number', 'phone', 'whatsapp', 'email', 'address', 'ticket_terms',
            # 3. Métier
            'currency', 'vat_rate', 'timezone', 'booking_cutoff_minutes', 'cancellation_deadline_hours',
            # 4. Matériel
            'printer_format', 'scanner_enabled', 'scale_enabled',
            # 5. Notifications
            'notify_sms_booking', 'notify_sms_reminder', 'notify_email_ticket', 'notify_agent_sound',
        ]
        widgets = {
            'theme_mode': forms.Select(attrs={'class': 'form-select'}),
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color w-100', 'style': 'height: 40px; cursor: pointer;'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'date_format': forms.Select(attrs={'class': 'form-select'}),
            'time_format': forms.Select(attrs={'class': 'form-select'}),
            
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: General Express Voyages'}),
            'legal_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: General Express Voyages S.A.'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: M0192837465A / RC-DLA-2015-B-102'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: N° MINT-TRANS-CMR/2024-AGY'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: +237 656 055 407'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: +237 699 000 111'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@general-express.cm'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Siège social, Ville, Quartier, Carrefour...'}),
            'ticket_terms': forms.Textarea(attrs={'class': 'form-control font-monospace small', 'rows': 4}),
            
            'currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'FCFA'}),
            'vat_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Africa/Douala'}),
            'booking_cutoff_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_deadline_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            
            'printer_format': forms.Select(attrs={'class': 'form-select'}),
            'scanner_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'scale_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            'notify_sms_booking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_sms_reminder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_email_ticket': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_agent_sound': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['vehicle_type', 'capacity', 'amenities', 'registration', 'status']
        labels = {
            'vehicle_type': 'Type de véhicule',
            'capacity': 'Capacité (nombre de places)',
            'amenities': 'Équipements & Confort',
            'registration': 'Numéro d\'immatriculation',
            'status': 'Disponibilité opérationnelle',
        }
        widgets = {
            'vehicle_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bus VIP 70 places, Coaster...'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 70'}),
            'amenities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: Climatisation, Wi-Fi, Prises USB, Sièges inclinables VIP'}),
            'registration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: LT-245-AB'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_capacity(self):
        new_capacity = self.cleaned_data.get('capacity')
        if self.instance and self.instance.pk and new_capacity:
            from django.utils import timezone
            today = timezone.localdate()
            # Vérifier que la réduction de capacité ne casse pas des réservations déjà validées
            future_deps = self.instance.departures.filter(
                date__gte=today
            ).exclude(status__in=['departed', 'cancelled'])
            for dep in future_deps:
                if dep.booked_seats > new_capacity:
                    raise forms.ValidationError(
                        f"Impossible de réduire la capacité à {new_capacity} places : "
                        f"le départ du {dep.date.strftime('%d/%m/%Y')} à {dep.time.strftime('%H:%M')} "
                        f"sur '{dep.line.name}' compte déjà {dep.booked_seats} réservations actives."
                    )
        return new_capacity

class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['first_name', 'last_name', 'phone', 'license_number', 'is_active']
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom de famille',
            'phone': 'Numéro de téléphone',
            'license_number': 'N° Permis de conduire (Catégorie D)',
            'is_active': 'En service / Disponible',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Jean-Marc'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Tchouassi'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 677 89 01 23'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: CE-2018-D-0921'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DepartureForm(forms.ModelForm):
    class Meta:
        model = Departure
        fields = ['line', 'vehicle', 'driver', 'date', 'time']
        labels = {
            'line': 'Ligne / Trajet',
            'vehicle': 'Véhicule assigné',
            'driver': 'Chauffeur assigné',
            'date': 'Date de départ',
            'time': 'Heure de départ',
        }
        widgets = {
            'line': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'driver': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'text', 
                'placeholder': 'JJ/MM/AAAA', 
                'id': 'departure-form-date'
            }),
            'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }
        
    def __init__(self, *args, **kwargs):
        agency = kwargs.pop('agency', None)
        super().__init__(*args, **kwargs)
        if agency:
            # Véhicules disponibles uniquement (ou le véhicule actuellement assigné si modification)
            from django.db.models import Q
            veh_qs = Vehicle.objects.filter(agency=agency)
            if self.instance and self.instance.pk and self.instance.vehicle:
                self.fields['vehicle'].queryset = veh_qs.filter(
                    Q(status='available') | Q(id=self.instance.vehicle.id)
                )
            else:
                self.fields['vehicle'].queryset = veh_qs.filter(status='available')

            self.fields['line'].queryset = Line.objects.filter(agency=agency)
            self.fields['driver'].queryset = Driver.objects.filter(agency=agency, is_active=True)
            self.fields['driver'].required = False

    def clean(self):
        cleaned_data = super().clean()
        line = cleaned_data.get('line')
        vehicle = cleaned_data.get('vehicle')
        driver = cleaned_data.get('driver')
        dep_date = cleaned_data.get('date')
        dep_time = cleaned_data.get('time')

        if not (dep_date and dep_time and line):
            return cleaned_data

        from django.utils import timezone
        from datetime import datetime, timedelta
        now = timezone.localtime()

        # 0. Interdiction absolue des départs dans le passé
        if dep_date < now.date() or (dep_date == now.date() and dep_time <= now.time()):
            self.add_error('time', "Impossible de programmer un départ à un horaire déjà dépassé.")
            return cleaned_data

        # 1. Disponibilité opérationnelle du véhicule
        if vehicle and vehicle.status != 'available':
            if not self.instance or self.instance.vehicle != vehicle:
                self.add_error(
                    'vehicle', 
                    f"Le véhicule '{vehicle.registration or vehicle.vehicle_type}' est actuellement indisponible (Statut : {vehicle.get_status_display()})."
                )

        start_dt = datetime.combine(dep_date, dep_time)
        trip_duration = line.get_duration()
        end_dt = start_dt + trip_duration

        dep_start_city = line.departure_city
        dep_end_city = line.arrival_city

        # 2. VÉRIFICATION RIGOUREUSE DES CONFLITS POUR LE VÉHICULE
        if vehicle:
            existing_veh_deps = Departure.objects.filter(
                vehicle=vehicle
            ).exclude(status__in=['departed', 'cancelled']).select_related('line')

            if self.instance and self.instance.pk:
                existing_veh_deps = existing_veh_deps.exclude(pk=self.instance.pk)

            for other_dep in existing_veh_deps:
                other_start = other_dep.get_trip_start_datetime()
                other_end = other_dep.get_trip_end_datetime()
                
                # A. Chevauchement temporel strict avec marge de battement (30 min)
                if start_dt < (other_end + timedelta(minutes=30)) and (end_dt + timedelta(minutes=30)) > other_start:
                    self.add_error(
                        'vehicle',
                        f"Conflit de véhicule : Le bus '{vehicle.registration or vehicle.vehicle_type}' "
                        f"est déjà affecté au voyage '{other_dep.line.name}' le {other_dep.date.strftime('%d/%m/%Y')} "
                        f"de {other_dep.time.strftime('%H:%M')} à {other_end.strftime('%H:%M')} "
                        f"(durée de trajet estimée : {other_dep.line.get_duration()})."
                    )
                    break

                # B. Cohérence d'acheminement géographique (Lieu d'arrivée vs départ suivant)
                if other_dep.date == dep_date:
                    # Si other_dep précède ce voyage
                    if other_end <= start_dt:
                        if other_dep.end_city and dep_start_city and other_dep.end_city != dep_start_city:
                            self.add_error(
                                'vehicle',
                                f"Incohérence géographique : Le bus termine son voyage précédent à {other_dep.end_city} à {other_end.strftime('%H:%M')}, "
                                f"or ce nouveau voyage part de {dep_start_city}. Un délai de convoyage est obligatoire."
                            )
                            break

        # 3. VÉRIFICATION RIGOUREUSE DES CONFLITS POUR LE CHAUFFEUR
        if driver:
            existing_driver_deps = Departure.objects.filter(
                driver=driver
            ).exclude(status__in=['departed', 'cancelled']).select_related('line')

            if self.instance and self.instance.pk:
                existing_driver_deps = existing_driver_deps.exclude(pk=self.instance.pk)

            for other_dep in existing_driver_deps:
                other_start = other_dep.get_trip_start_datetime()
                other_end = other_dep.get_trip_end_datetime()

                # A. Chevauchement temporel strict avec temps de repos obligatoire (45 min)
                if start_dt < (other_end + timedelta(minutes=45)) and (end_dt + timedelta(minutes=45)) > other_start:
                    self.add_error(
                        'driver',
                        f"Conflit de chauffeur : Le conducteur '{driver.full_name}' "
                        f"est déjà affecté au voyage '{other_dep.line.name}' le {other_dep.date.strftime('%d/%m/%Y')} "
                        f"de {other_dep.time.strftime('%H:%M')} à {other_end.strftime('%H:%M')} "
                        f"(temps de route et repos obligatoire de 45 min requis avant le voyage suivant)."
                    )
                    break

                # B. Cohérence géographique du conducteur (Ville d'arrivée vs Ville de départ)
                if other_dep.date == dep_date:
                    if other_end <= start_dt:
                        if other_dep.end_city and dep_start_city and other_dep.end_city != dep_start_city:
                            self.add_error(
                                'driver',
                                f"Incohérence géographique : Le chauffeur {driver.full_name} arrive à {other_dep.end_city} vers {other_end.strftime('%H:%M')}, "
                                f"mais ce départ est programmé au départ de {dep_start_city}. Le chauffeur ne peut pas assurer ce voyage."
                            )
                            break

        return cleaned_data


class AgencyBookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'departure', 'departure_stop', 'arrival_stop',
            'traveler_name', 'traveler_phone', 'traveler_email',
            'id_type', 'id_number', 'seats_reserved',
            'payment_method', 'payment_status'
        ]
        labels = {
            'departure': 'Départ / Voyage',
            'departure_stop': 'Arrêt de montée (Départ)',
            'arrival_stop': 'Arrêt de descente (Arrivée)',
            'traveler_name': 'Nom complet du voyageur',
            'traveler_phone': 'Téléphone de contact',
            'traveler_email': 'Adresse email (optionnelle)',
            'id_type': 'Pièce d\'identité',
            'id_number': 'Numéro de la pièce',
            'seats_reserved': 'Nombre de places',
            'payment_method': 'Mode d\'encaissement',
            'payment_status': 'Statut du règlement',
        }
        widgets = {
            'departure': forms.Select(attrs={'class': 'form-select', 'id': 'booking-departure-select'}),
            'departure_stop': forms.Select(attrs={'class': 'form-select', 'id': 'booking-start-stop-select'}),
            'arrival_stop': forms.Select(attrs={'class': 'form-select', 'id': 'booking-end-stop-select'}),
            'traveler_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Kamgaing Jean-Paul'}),
            'traveler_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 656 055 407 ou +237 6...'}),
            'traveler_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ex: voyageur@domaine.com'}),
            'id_type': forms.Select(attrs={'class': 'form-select'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 102938475'}),
            'seats_reserved': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'id': 'booking-seats-input'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        agency = kwargs.pop('agency', None)
        selected_departure = kwargs.pop('departure', None)
        super().__init__(*args, **kwargs)
        self.fields['traveler_email'].required = False
        
        from travel.models import LineStop, Departure
        from django.utils import timezone
        from django.db.models import Q

        if agency:
            now = timezone.localtime()
            today = now.date()
            current_time = now.time()
            departures_qs = Departure.objects.filter(
                agency=agency, 
                status__in=['scheduled', 'boarding'],
                available_capacity__gt=0
            ).filter(
                Q(date__gt=today) | Q(date=today, time__gt=current_time)
            ).select_related('line', 'vehicle').order_by('date', 'time')
            self.fields['departure'].queryset = departures_qs
            self.fields['departure'].label_from_instance = (
                lambda d: f"{d.line.name} • {d.date.strftime('%d/%m/%Y')} à {d.time.strftime('%H:%M')} • {d.available_capacity} pl. libres ({d.vehicle.registration if d.vehicle else 'Bus standard'})"
            )
            
            dep = selected_departure
            if not dep and self.data and self.data.get('departure'):
                try:
                    dep = departures_qs.get(id=self.data.get('departure'))
                except (Departure.DoesNotExist, ValueError):
                    dep = None
            if not dep and departures_qs.exists():
                dep = departures_qs.first()
                
            if dep:
                stops_qs = LineStop.objects.filter(line=dep.line).select_related('city').order_by('stop_order')
                self.fields['departure_stop'].queryset = stops_qs
                self.fields['arrival_stop'].queryset = stops_qs
                if not self.is_bound:
                    self.fields['departure'].initial = dep.id
                    first_stop = stops_qs.first()
                    last_stop = stops_qs.last()
                    if first_stop:
                        self.fields['departure_stop'].initial = first_stop.id
                    if last_stop:
                        self.fields['arrival_stop'].initial = last_stop.id
            else:
                self.fields['departure_stop'].queryset = LineStop.objects.none()
                self.fields['arrival_stop'].queryset = LineStop.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        departure = cleaned_data.get('departure')
        departure_stop = cleaned_data.get('departure_stop')
        arrival_stop = cleaned_data.get('arrival_stop')
        seats = cleaned_data.get('seats_reserved') or 1
        phone = cleaned_data.get('traveler_phone')

        if departure:
            if departure.is_closed_for_sale():
                self.add_error('departure', "Ce départ est clôturé à la vente (déjà parti ou horaire dépassé).")
            elif seats > departure.available_capacity:
                self.add_error('seats_reserved', f"Capacité insuffisante : seulement {departure.available_capacity} place(s) disponible(s).")

        if departure_stop and arrival_stop:
            if departure_stop.stop_order >= arrival_stop.stop_order:
                self.add_error('arrival_stop', "L'arrêt d'arrivée doit être situé après l'arrêt de départ.")

        if phone:
            from accounts.validators import validate_cameroon_phone
            try:
                cleaned_data['traveler_phone'] = validate_cameroon_phone(phone)
            except forms.ValidationError as e:
                self.add_error('traveler_phone', e)
        return cleaned_data
