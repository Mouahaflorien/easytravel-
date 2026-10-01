from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import User
from .validators import validate_cameroon_phone, validate_clean_email, validate_identity_info
from bookings.models import Booking

def traveler_login(request):
    next_url = request.GET.get('next') or request.POST.get('next') or 'travel:home'
    
    if request.user.is_authenticated:
        if next_url and next_url != 'travel:home':
            return redirect(next_url)
        return redirect('accounts:my_bookings')
        
    login_error = None
    
    if request.method == 'POST' and 'action_login' in request.POST:
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        
        # Permettre la connexion par nom d'utilisateur ou par email
        user = None
        if '@' in identifier:
            user_obj = User.objects.filter(email__iexact=identifier).first()
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)
        else:
            user = authenticate(request, username=identifier, password=password)
            
        if user is not None:
            login(request, user)
            messages.success(request, f"Ravi de vous revoir, {user.first_name or user.username} !")
            return redirect(next_url)
        else:
            login_error = "Identifiant ou mot de passe incorrect."
            
    return render(request, 'accounts/login.html', {
        'next': next_url,
        'login_error': login_error,
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
            if not full_name:
                raise ValidationError("Le nom complet est obligatoire.")
            if len(password) < 6:
                raise ValidationError("Le mot de passe doit comporter au moins 6 caractères.")
            if password != password_confirm:
                raise ValidationError("Les mots de passe ne correspondent pas.")
                
            clean_email = validate_clean_email(email_raw)
            if User.objects.filter(email__iexact=clean_email).exists():
                raise ValidationError("Cette adresse email est déjà associée à un compte.")
                
            clean_phone = validate_cameroon_phone(phone_raw)
            id_type, clean_id_number = validate_identity_info(id_type, id_number)
            
            # Générer un username unique à partir de l'email
            username_base = clean_email.split('@')[0]
            username = username_base
            count = 1
            while User.objects.filter(username=username).exists():
                username = f"{username_base}{count}"
                count += 1
                
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            user = User.objects.create_user(
                username=username,
                email=clean_email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=clean_phone,
                id_type=id_type,
                id_number=clean_id_number,
                role='traveler'
            )
            
            login(request, user)
            messages.success(request, f"Votre compte voyageur a été créé avec succès ! Bienvenue, {first_name}.")
            return redirect(next_url)
            
        except ValidationError as e:
            reg_error = e.message if hasattr(e, 'message') else str(e)
            
    return render(request, 'accounts/login.html', {
        'next': next_url,
        'reg_error': reg_error,
        'active_tab': 'register',
        'reg_data': request.POST if request.method == 'POST' else {}
    })


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
