from urllib.parse import quote
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from travel.models import Departure, LineStop
from accounts.validators import validate_cameroon_phone, validate_clean_email, validate_identity_info
from .models import Booking

@login_required(login_url='accounts:login')
def book_departure(request, departure_id):
    departure = get_object_or_404(
        Departure.objects.select_related('agency', 'line', 'vehicle'), 
        id=departure_id
    )
    
    start_id = request.GET.get('start') or request.POST.get('start_id')
    end_id = request.GET.get('end') or request.POST.get('end_id')
    
    if not start_id or not end_id:
        return redirect('travel:home')
        
    start_stop = get_object_or_404(LineStop.objects.select_related('city'), id=start_id)
    end_stop = get_object_or_404(LineStop.objects.select_related('city'), id=end_id)
    segment_price = end_stop.price_from_start - start_stop.price_from_start
    
    error = None
    form_data = {
        'name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
        'email': request.user.email,
        'phone': request.user.phone,
        'id_type': getattr(request.user, 'id_type', 'CNI') or 'CNI',
        'id_number': getattr(request.user, 'id_number', ''),
        'seats': 1,
    }
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_raw = request.POST.get('phone', '').strip()
        email_raw = request.POST.get('email', '').strip()
        id_type_raw = request.POST.get('id_type', 'CNI').strip()
        id_number_raw = request.POST.get('id_number', '').strip()
        
        try:
            seats = int(request.POST.get('seats', 1))
        except (ValueError, TypeError):
            seats = 1
            
        form_data = {
            'name': name,
            'phone': phone_raw,
            'email': email_raw,
            'id_type': id_type_raw,
            'id_number': id_number_raw,
            'seats': seats,
        }
        
        try:
            # 1. Validation du Nom
            if not name or len(name) < 3:
                raise ValidationError("Le nom complet du passager est obligatoire (au moins 3 caractères).")
                
            # 2. Validation stricte du téléphone camerounais
            clean_phone = validate_cameroon_phone(phone_raw)
            
            # 3. Validation stricte de l'email
            clean_email = validate_clean_email(email_raw)
            
            # 4. Validation obligatoire de la pièce d'identité (CNI / Passeport / Récépissé)
            clean_id_type, clean_id_number = validate_identity_info(id_type_raw, id_number_raw)
            
            # 5. Vérification de la disponibilité
            if seats < 1:
                raise ValidationError("Vous devez réserver au moins 1 place.")
            if seats > departure.available_capacity:
                raise ValidationError(f"Capacité insuffisante : il ne reste que {departure.available_capacity} place(s) disponible(s).")
                
            total_amount = segment_price * seats
            
            # 6. Création de la réservation liée au compte utilisateur
            booking = Booking.objects.create(
                user=request.user,
                departure=departure,
                departure_stop=start_stop,
                arrival_stop=end_stop,
                traveler_name=name,
                traveler_phone=clean_phone,
                traveler_email=clean_email,
                id_type=clean_id_type,
                id_number=clean_id_number,
                seats_reserved=seats,
                total_amount=total_amount,
                status='confirmed',
                payment_status='pending',
                payment_method='online'
            )
            
            # Mise à jour des informations de l'utilisateur si non renseignées
            user_updated = False
            if not request.user.phone and clean_phone:
                request.user.phone = clean_phone
                user_updated = True
            if not request.user.id_number and clean_id_number:
                request.user.id_type = clean_id_type
                request.user.id_number = clean_id_number
                user_updated = True
            if user_updated:
                request.user.save()
                
            # Déduction de la capacité
            departure.available_capacity -= seats
            departure.save()
            
            return redirect('bookings:confirmation', reference=booking.reference)
            
        except ValidationError as e:
            error = e.message if hasattr(e, 'message') else str(e)
            
    return render(request, 'bookings/book.html', {
        'departure': departure, 
        'start_stop': start_stop, 
        'end_stop': end_stop, 
        'segment_price': segment_price,
        'form_data': form_data,
        'error': error,
    })


def booking_confirmation(request, reference):
    booking = get_object_or_404(
        Booking.objects.select_related(
            'departure', 'departure__agency', 'departure__vehicle',
            'departure_stop__city', 'arrival_stop__city', 'user'
        ),
        reference=reference
    )
    
    # Données du QR Code pour contrôle / vérification
    verify_url = request.build_absolute_uri()
    start_city = booking.departure_stop.city.name if booking.departure_stop and booking.departure_stop.city else "Départ"
    end_city = booking.arrival_stop.city.name if booking.arrival_stop and booking.arrival_stop.city else "Arrivée"
    
    qr_payload = f"REF:{booking.reference}|NOM:{booking.traveler_name}|PIECE:{booking.id_type}-{booking.id_number}|TRAJET:{start_city}-{end_city}|DATE:{booking.departure.date}|PLACES:{booking.seats_reserved}"
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={quote(qr_payload)}"
    
    return render(request, 'bookings/confirmation.html', {
        'booking': booking,
        'start_city': start_city,
        'end_city': end_city,
        'qr_code_url': qr_code_url,
    })
