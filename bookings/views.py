from urllib.parse import quote
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.exceptions import ValidationError
from travel.models import Departure, LineStop
from accounts.models import User
from accounts.validators import (
    validate_cameroon_phone, 
    validate_clean_email, 
    validate_identity_info,
    validate_passenger_name
)
from accounts.services.email_service import send_account_activation_email
from .models import Booking
import qrcode
import base64
from io import BytesIO
from django.contrib import messages


def book_departure(request, departure_id):
    """
    Vue de réservation d'un voyage :
    - Si l'utilisateur est connecté : réservation instantanée confirmée.
    - Si l'utilisateur n'a pas de compte : création du compte en attente (is_active=False) 
      et envoi immédiat d'un lien d'activation par email requis pour valider le compte et le billet.
    """
    # Nettoyage des réservations impayées expirées
    Booking.cancel_expired_pending_bookings()
    
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
    is_auth = request.user.is_authenticated
    current_user = request.user if is_auth else None

    form_data = {
        'name': f"{current_user.first_name} {current_user.last_name}".strip() if current_user else '',
        'email': current_user.email if current_user else '',
        'phone': current_user.phone if current_user else '',
        'id_type': getattr(current_user, 'id_type', 'CNI') if current_user else 'CNI',
        'id_number': getattr(current_user, 'id_number', '') if current_user else '',
        'seats': 1,
    }
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_raw = request.POST.get('phone', '').strip()
        email_raw = request.POST.get('email', '').strip()
        id_type_raw = request.POST.get('id_type', 'CNI').strip()
        id_number_raw = request.POST.get('id_number', '').strip()
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
            'id_number': id_number_raw,
            'seats': seats,
        }
        
        try:
            # 1. Validation stricte du Nom (état civil, au moins 2 mots, sans symboles/mots factices)
            clean_name = validate_passenger_name(name)
                
            # 2. Validation stricte du téléphone (Cameroun ou international)
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

            # CAS 1 : L'utilisateur est déjà connecté
            if is_auth:
                booking = Booking.objects.create(
                    user=request.user,
                    departure=departure,
                    departure_stop=start_stop,
                    arrival_stop=end_stop,
                    traveler_name=clean_name,
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
                
                # Mise à jour du profil si non renseigné
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

            # CAS 2 : Nouvel utilisateur ou voyageur non connecté -> Création de compte & validation obligatoire par lien email
            else:
                if len(password) < 6:
                    raise ValidationError("Veuillez choisir un mot de passe d'au moins 6 caractères pour sécuriser votre compte voyageur.")
                if password != password_confirm:
                    raise ValidationError("Les mots de passe saisis ne correspondent pas.")

                existing_user = User.objects.filter(email__iexact=clean_email).first()
                if existing_user and existing_user.is_active:
                    raise ValidationError(
                        "Cette adresse email est déjà liée à un compte actif. Veuillez vous connecter avec vos identifiants pour continuer votre réservation."
                    )

                name_parts = clean_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''

                if existing_user:
                    target_user = existing_user
                    target_user.set_password(password)
                    target_user.first_name = first_name
                    target_user.last_name = last_name
                    target_user.phone = clean_phone
                    target_user.id_type = clean_id_type
                    target_user.id_number = clean_id_number
                    target_user.save()
                else:
                    username_base = clean_email.split('@')[0]
                    username = username_base
                    count = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{username_base}{count}"
                        count += 1

                    target_user = User.objects.create_user(
                        username=username,
                        email=clean_email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        phone=clean_phone,
                        id_type=clean_id_type,
                        id_number=clean_id_number,
                        role='traveler',
                        is_active=False
                    )

                # Création de la réservation en statut 'pending' (en attente d'authentification par email)
                booking = Booking.objects.create(
                    user=target_user,
                    departure=departure,
                    departure_stop=start_stop,
                    arrival_stop=end_stop,
                    traveler_name=clean_name,
                    traveler_phone=clean_phone,
                    traveler_email=clean_email,
                    id_type=clean_id_type,
                    id_number=clean_id_number,
                    seats_reserved=seats,
                    total_amount=total_amount,
                    status='pending',
                    payment_status='pending',
                    payment_method='online'
                )

                # Envoi du mail d'authentification lié à cette réservation
                confirmation_url = reverse('bookings:confirmation', kwargs={'reference': booking.reference})
                send_account_activation_email(request, target_user, next_url=confirmation_url, booking=booking)

                request.session['activation_email'] = clean_email
                request.session['pending_booking_ref'] = booking.reference
                return redirect(f"{reverse('accounts:activation_pending')}?booking={booking.reference}&email={quote(clean_email)}")
            
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
    
    # Vérification IDOR : Bloquer l'accès aux autres utilisateurs
    if booking.user and booking.user != request.user:
        messages.error(request, "Accès non autorisé à cette réservation.")
        return redirect('travel:home')
        
    # Données du QR Code pour contrôle / vérification
    verify_url = request.build_absolute_uri()
    start_city = booking.departure_stop.city.name if booking.departure_stop and booking.departure_stop.city else "Départ"
    end_city = booking.arrival_stop.city.name if booking.arrival_stop and booking.arrival_stop.city else "Arrivée"
    
    qr_payload = f"REF:{booking.reference}|NOM:{booking.traveler_name}|PIECE:{booking.id_type}-{booking.id_number}|TRAJET:{start_city}-{end_city}|DATE:{booking.departure.date}|PLACES:{booking.seats_reserved}"
    
    # Génération LOCALE et sécurisée du QR Code (sans fuite de données)
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    qr_code_url = f"data:image/png;base64,{qr_base64}"
    
    return render(request, 'bookings/confirmation.html', {
        'booking': booking,
        'start_city': start_city,
        'end_city': end_city,
        'qr_code_url': qr_code_url,
    })
