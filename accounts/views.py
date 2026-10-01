from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import User
from .validators import (
    validate_cameroon_phone, 
    validate_clean_email, 
    validate_identity_info,
    validate_passenger_name
)
from .services.email_service import send_account_activation_email, verify_activation_token
from bookings.models import Booking

def traveler_login(request):
    next_url = request.GET.get('next') or request.POST.get('next') or 'travel:home'
    
    if request.user.is_authenticated:
        if next_url and next_url != 'travel:home':
            return redirect(next_url)
        return redirect('accounts:my_bookings')
        
    login_error = None
    unactivated_email = None
    
    if request.method == 'POST' and 'action_login' in request.POST:
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        
        # Permettre la connexion par nom d'utilisateur ou par email
        user = None
        candidate = None
        if '@' in identifier:
            candidate = User.objects.filter(email__iexact=identifier).first()
        else:
            candidate = User.objects.filter(username__iexact=identifier).first()

        if candidate:
            user = authenticate(request, username=candidate.username, password=password)
            
        if user is not None:
            login(request, user)
            messages.success(request, f"Ravi de vous revoir, {user.first_name or user.username} !")
            return redirect(next_url)
        else:
            # Vérifier si le compte existe avec le bon mot de passe mais n'est pas encore activé
            if candidate and candidate.check_password(password) and not candidate.is_active:
                login_error = "inactive_account"
                unactivated_email = candidate.email
            else:
                login_error = "Identifiant ou mot de passe incorrect."
            
    return render(request, 'accounts/login.html', {
        'next': next_url,
        'login_error': login_error,
        'unactivated_email': unactivated_email,
    })


def traveler_register(request):
    next_url = request.GET.get('next') or request.POST.get('next') or 'travel:home'
    
    if request.user.is_authenticated:
        return redirect(next_url)
        
    reg_error = None
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email_raw = request.POST.get('email', '').strip()
        phone_raw = request.POST.get('phone', '').strip()
        id_type = request.POST.get('id_type', 'CNI')
        id_number = request.POST.get('id_number', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        try:
            # 1. Validation rigoureuse du nom complet
            clean_name = validate_passenger_name(full_name)

            # 2. Validation du mot de passe
            if len(password) < 6:
                raise ValidationError("Le mot de passe doit comporter au moins 6 caractères.")
            if password != password_confirm:
                raise ValidationError("Les mots de passe saisis ne correspondent pas.")
                
            # 3. Validation de l'adresse email
            clean_email = validate_clean_email(email_raw)
            if User.objects.filter(email__iexact=clean_email).exists():
                raise ValidationError("Cette adresse email est déjà associée à un compte EasyTravel.")
                
            # 4. Validation stricte du téléphone (Cameroun ou international)
            clean_phone = validate_cameroon_phone(phone_raw)

            # 5. Validation rigoureuse de la pièce d'identité (CNI, Passeport, Récépissé)
            clean_id_type, clean_id_number = validate_identity_info(id_type, id_number)
            
            # Générer un nom d'utilisateur unique
            username_base = clean_email.split('@')[0]
            username = username_base
            count = 1
            while User.objects.filter(username=username).exists():
                username = f"{username_base}{count}"
                count += 1
                
            name_parts = clean_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Création du compte inactif en attente d'authentification par email
            user = User.objects.create_user(
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
            
            # Envoi du lien d'activation sécurisé par email
            send_account_activation_email(request, user)
            
            request.session['activation_email'] = clean_email
            return redirect('accounts:activation_pending')
            
        except ValidationError as e:
            reg_error = e.message if hasattr(e, 'message') else str(e)
            
    return render(request, 'accounts/login.html', {
        'next': next_url,
        'reg_error': reg_error,
        'active_tab': 'register',
        'reg_data': request.POST if request.method == 'POST' else {}
    })


def activation_pending(request):
    """
    Affiche la page d'information invitant l'utilisateur à valider son email.
    """
    email = request.GET.get('email') or request.session.get('activation_email', '')
    return render(request, 'accounts/activation_pending.html', {
        'email': email
    })


def activate_account(request, uidb64, token):
    """
    Valide le jeton d'authentification reçu par email et active le compte voyageur.
    """
    user = verify_activation_token(uidb64, token)
    
    if user is not None:
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, f"Félicitations {user.first_name or user.username} ! Votre compte est activé avec succès. Bienvenue sur EasyTravel.")
        return redirect('accounts:my_bookings')
    else:
        return render(request, 'accounts/activation_invalid.html')


def resend_activation(request):
    """
    Permet de renvoyer le lien d'activation par email si non reçu.
    """
    email = ''
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
    elif request.method == 'GET':
        email = request.GET.get('email', '').strip() or request.session.get('activation_email', '')

    if email:
        user = User.objects.filter(email__iexact=email).first()
        if user:
            if user.is_active:
                messages.info(request, "Ce compte est déjà actif. Vous pouvez vous connecter directement.")
                return redirect('accounts:login')
            else:
                send_account_activation_email(request, user)
                messages.success(request, f"Un nouvel email d'activation a été envoyé à {email}.")
        else:
            messages.info(request, f"Si un compte inactif est associé à {email}, un lien d'activation a été envoyé.")
            
        request.session['activation_email'] = email
        return redirect('accounts:activation_pending')

    return render(request, 'accounts/activation_invalid.html')


def traveler_logout(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('travel:home')


@login_required(login_url='accounts:login')
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related(
        'departure', 'departure__agency', 'departure__vehicle',
        'departure_stop__city', 'arrival_stop__city'
    ).order_by('-created_at')
    
    return render(request, 'accounts/my_bookings.html', {
        'bookings': bookings
    })

