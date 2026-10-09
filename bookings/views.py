from urllib.parse import quote
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.exceptions import ValidationError
from travel.models import Departure, LineStop
from accounts.models import User
from accounts.validators import (
    validate_cameroon_phone, 
    validate_clean_email, 
    validate_passenger_name
)
from accounts.services.email_service import send_account_activation_email
from .models import Booking
import qrcode
import base64
import hmac
import hashlib
from io import BytesIO
from django.contrib import messages
from django.conf import settings
from django.db import transaction


def book_departure(request, departure_id):
    """
    Vue de réservation d'un voyage :
    - Trajet défini automatiquement du premier au dernier arrêt de la ligne.
    - Réservation sans numéro de CNI obligatoire.
    """
    departure = get_object_or_404(
        Departure.objects.select_related('agency', 'line', 'vehicle'), 
        id=departure_id
    )
    
    # Automatisation : Point de départ et d'arrivée
    start_stop = departure.line.stops.order_by('stop_order').first()
    end_stop = departure.line.stops.order_by('-stop_order').first()
    
    if not start_stop or not end_stop or start_stop == end_stop:
        messages.error(request, "Erreur de configuration de la ligne de voyage.")
        return redirect('travel:home')
        
    segment_price = departure.line.base_price
    if segment_price <= 0:
        messages.error(request, "Tarif calculé invalide.")
        return redirect('travel:home')
    
    error = None
    is_auth = request.user.is_authenticated
    current_user = request.user if is_auth else None

    form_data = {
        'name': f"{current_user.first_name} {current_user.last_name}".strip() if current_user else '',
        'email': current_user.email if current_user else '',
        'phone': current_user.phone if current_user else '',
        'id_type': getattr(current_user, 'id_type', 'none') if current_user else 'none',
        'seats': 1,
    }
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_raw = request.POST.get('phone', '').strip()
        email_raw = request.POST.get('email', '').strip()
        id_type_raw = request.POST.get('id_type', 'none').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        try:
            seats = int(request.POST.get('seats', 1))
        except (ValueError, TypeError):
            seats = 1
            
        form_data = {
            'name': name,
            'phone': phone_raw,
            'email': email_raw,
            'id_type': id_type_raw,
            'seats': seats,
        }
        
        try:
            clean_name = validate_passenger_name(name)
            clean_phone = validate_cameroon_phone(phone_raw)
            
            # Email is optional. If provided, validate it. Otherwise, create a placeholder for account creation.
            if email_raw:
                clean_email = validate_clean_email(email_raw)
            else:
                # Generate a unique placeholder email using the clean phone number
                clean_email = f"user_{clean_phone.replace(' ', '').replace('+', '')}@easytravel.local"
                
            clean_id_number = "" # On ne stocke plus le numéro
            
            with transaction.atomic():
                departure.refresh_from_db()
                if departure.available_capacity < seats:
                    raise ValidationError(f"Désolé, il ne reste que {departure.available_capacity} places.")
                
                # Gestion Utilisateur
                if not is_auth:
                    if User.objects.filter(phone=clean_phone).exists():
                        raise ValidationError("Ce numéro de téléphone est déjà associé à un compte. Veuillez vous connecter.")
                    
                    # Generate a random 6-character password for the user
                    import random
                    import string
                    generated_password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                    
                    user = User.objects.create_user(
                        phone=clean_phone,
                        password=generated_password,
                        first_name=clean_name.split()[0],
                        last_name=' '.join(clean_name.split()[1:]) if len(clean_name.split()) > 1 else "",
                        email=clean_email,
                        id_type=id_type_raw,
                        id_number=clean_id_number,
                        is_active=False
                    )
                    
                    # Remplacement Email -> WhatsApp pour l'activation
                    try:
                        from accounts.services.whatsapp_service import send_whatsapp_activation
                        send_whatsapp_activation(user, request)
                    except Exception as e:
                        print("Erreur envoi whatsapp:", e)
                        pass
                        
                    messages.success(request, "Un message WhatsApp d'activation vous a été envoyé. Le billet est réservé.")
                else:
                    user = current_user
                
                # Extraction des accompagnants
                companions_list = []
                for i in range(2, seats + 1):
                    comp_name = request.POST.get(f'traveler_name_{i}', '').strip()
                    comp_id_type = request.POST.get(f'id_type_{i}', 'none').strip()
                    if comp_name:
                        companions_list.append({
                            'name': comp_name,
                            'id_type': comp_id_type
                        })
                
                # Création Réservation
                booking = Booking.objects.create(
                    user=user,
                    departure=departure,
                    departure_stop=start_stop,
                    arrival_stop=end_stop,
                    traveler_name=clean_name,
                    traveler_phone=clean_phone,
                    traveler_email=clean_email,
                    id_type=id_type_raw,
                    id_number=clean_id_number,
                    companions=companions_list,
                    seats_reserved=seats,
                    total_amount=segment_price * seats,
                    payment_status='pending',
                    status='pending'
                )
                
                departure.available_capacity -= seats
                departure.save()
                
                return redirect(reverse('bookings:checkout', args=[booking.reference]))
                
        except ValidationError as e:
            error = e.message
            messages.error(request, error)
            
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
    
    # Vérification IDOR : Bloquer l'accès aux autres utilisateurs
    if booking.user and booking.user != request.user:
        # Autoriser les agents d'agence à consulter les billets
        is_agency_staff = request.user.is_authenticated and (
            request.user.is_staff or 
            request.user.is_superuser or 
            getattr(request.user, 'role', '') in ['manager', 'agent', 'admin']
        )
        if not is_agency_staff:
            messages.error(request, "Accès non autorisé à cette réservation.")
            return redirect('travel:home')
        
    # Données du QR Code pour contrôle / vérification
    verify_url = request.build_absolute_uri()
    start_city = booking.departure_stop.city.name if booking.departure_stop and booking.departure_stop.city else "Départ"
    end_city = booking.arrival_stop.city.name if booking.arrival_stop and booking.arrival_stop.city else "Arrivée"
    
    raw_payload = f"REF:{booking.reference}|NOM:{booking.traveler_name}|PIECE:{booking.id_type}-{booking.id_number}|TRAJET:{start_city}-{end_city}|DATE:{booking.departure.date}|PLACES:{booking.seats_reserved}"
    signature = hmac.new(settings.SECRET_KEY.encode(), raw_payload.encode(), hashlib.sha256).hexdigest()[:12]
    qr_payload = f"{raw_payload}|SIG:{signature}"
    # Génération LOCALE et sécurisée du QR Code (sans fuite de données)
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    qr_code_url = f"data:image/png;base64,{qr_base64}"
    
    layout = request.GET.get('layout')
    if layout == 'clean':
        base_template = 'agencies/base_clean_ticket.html'
    else:
        base_template = 'agencies/base_agency.html' if (
            request.user.is_authenticated and getattr(request.user, 'role', '') in ['manager', 'agent', 'admin']
        ) else 'travel/base.html'
    
    return render(request, 'bookings/confirmation.html', {
        'booking': booking,
        'start_city': start_city,
        'end_city': end_city,
        'qr_code_url': qr_code_url,
        'base_template': base_template,
    })

def booking_feedback_view(request, reference):
    """Vue pour recueillir la note de satisfaction du voyageur"""
    from .models import BookingFeedback
    booking = get_object_or_404(Booking, reference=reference)
    
    # Vérification IDOR : Seul le propriétaire peut laisser un avis
    if booking.user and booking.user != request.user:
        messages.error(request, "Accès non autorisé à cette réservation.")
        return redirect('travel:home')
    
    # Si un sondage a déjà été soumis pour ce billet, on affiche un message
    if hasattr(booking, 'feedback'):
        messages.info(request, "Vous avez déjà donné votre avis pour ce voyage, merci !")
        return redirect('travel:home')
        
    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 5))
            if rating < 1 or rating > 5:
                rating = 5
        except ValueError:
            rating = 5
            
        comment = request.POST.get('comment', '').strip()
        
        BookingFeedback.objects.create(
            booking=booking,
            rating=rating,
            comment=comment
        )
        
        messages.success(request, "Merci ! Votre avis a bien été enregistré. Il aidera l'agence à s'améliorer.")
        return redirect('travel:home')
        
    return render(request, 'bookings/feedback.html', {'booking': booking})
