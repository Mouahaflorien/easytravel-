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
import hmac
import hashlib
from io import BytesIO
from django.contrib import messages
from django.conf import settings


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
                
            agency_amount = segment_price * seats
            from decimal import Decimal
            percent = departure.agency.platform_fee_percentage if hasattr(departure.agency, 'platform_fee_percentage') else Decimal('3.00')
            platform_fee_percent = Decimal(str(percent)) / Decimal('100.0')
            platform_fee = agency_amount * platform_fee_percent
            total_amount = agency_amount + platform_fee

            with transaction.atomic():
                target_user = request.user if is_auth else None
                
                if not is_auth:
                    if len(password) < 6:
                        raise ValidationError("Veuillez choisir un mot de passe d'au moins 6 caractères pour sécuriser votre compte voyageur.")
                    if password != password_confirm:
                        raise ValidationError("Les mots de passe saisis ne correspondent pas.")
                    existing_user = User.objects.filter(email__iexact=clean_email).first()
                    if existing_user and existing_user.is_active:
                        raise ValidationError("Cette adresse email est déjà liée à un compte actif. Veuillez vous connecter avec vos identifiants pour continuer.")
                    
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
                            username=username, email=clean_email, password=password,
                            first_name=first_name, last_name=last_name, phone=clean_phone,
                            id_type=clean_id_type, id_number=clean_id_number,
                            role='traveler', is_active=False
                        )
                else:
                    user_updated = False
                    if not target_user.phone and clean_phone:
                        target_user.phone = clean_phone
                        user_updated = True
                    if not target_user.id_number and clean_id_number:
                        target_user.id_type = clean_id_type
                        target_user.id_number = clean_id_number
                        user_updated = True
                    if user_updated:
                        target_user.save()

                from bookings.models import BookingCart
                cart = None
                if seats > 1:
                    cart = BookingCart.objects.create(user=target_user, total_amount=total_amount)

                first_booking = None
                for i in range(1, seats + 1):
                    t_name = clean_name if i == 1 else request.POST.get(f'traveler_name_{i}', f"{clean_name} (Accompagnant {i})")
                    t_id_type = clean_id_type if i == 1 else request.POST.get(f'id_type_{i}', clean_id_type)
                    t_id_number = clean_id_number if i == 1 else request.POST.get(f'id_number_{i}', 'Non spécifié')

                    b = Booking.objects.create(
                        cart=cart,
                        user=target_user,
                        departure=departure,
                        departure_stop=start_stop,
                        arrival_stop=end_stop,
                        traveler_name=t_name,
                        traveler_phone=clean_phone,
                        traveler_email=clean_email,
                        id_type=t_id_type,
                        id_number=t_id_number,
                        seats_reserved=1,
                        agency_amount=agency_amount / seats,
                        platform_fee=platform_fee / seats,
                        total_amount=total_amount / seats,
                        status='confirmed' if is_auth else 'pending',
                        payment_status='pending',
                        payment_method='online'
                    )
                    if i == 1:
                        first_booking = b

                departure.available_capacity -= seats
                departure.save()

            if is_auth:
                return redirect('bookings:confirmation', reference=first_booking.reference)
            else:
                confirmation_url = reverse('bookings:confirmation', kwargs={'reference': first_booking.reference})
                send_account_activation_email(request, target_user, next_url=confirmation_url, booking=first_booking)
                request.session['activation_email'] = clean_email
                request.session['pending_booking_ref'] = first_booking.reference
                return redirect(f"{reverse('accounts:activation_pending')}?booking={first_booking.reference}&email={quote(clean_email)}")
            
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



from django.views.decorators.clickjacking import xframe_options_sameorigin

@xframe_options_sameorigin
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
