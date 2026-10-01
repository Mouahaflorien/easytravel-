import logging
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from accounts.models import User

logger = logging.getLogger(__name__)


def generate_activation_link(request, user):
    """
    Génère un lien d'activation sécurisé, unique et à usage unique pour l'utilisateur.
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    relative_path = reverse('accounts:activate_account', kwargs={'uidb64': uidb64, 'token': token})
    
    if request:
        return request.build_absolute_uri(relative_path)
    
    base_url = getattr(settings, 'SITE_URL', 'https://easytravel.mslogitech.com').rstrip('/')
    return f"{base_url}{relative_path}"


def send_account_activation_email(request, user):
    """
    Envoie un email HTML et texte contenant le lien d'activation sécurisé du compte voyageur.
    """
    try:
        activation_url = generate_activation_link(request, user)
        context = {
            'user': user,
            'activation_url': activation_url,
            'site_name': 'EasyTravel',
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@easytravel.mslogitech.com'),
        }

        subject = "[EasyTravel] Activez votre compte voyageur et confirmez votre adresse email"
        html_message = render_to_string('accounts/emails/activation_email.html', context)
        text_message = render_to_string('accounts/emails/activation_email.txt', context)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'EasyTravel <noreply@easytravel.mslogitech.com>')
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=from_email,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        logger.info(f"Email d'activation envoyé avec succès à {user.email} (ID: {user.pk})")
        return True
    except Exception as e:
        logger.error(f"Échec de l'envoi de l'email d'activation à {user.email}: {e}", exc_info=True)
        return False


def verify_activation_token(uidb64, token):
    """
    Vérifie l'authenticité et la validité du token d'activation.
    Retourne l'objet User si valide, sinon None.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None

    if user and default_token_generator.check_token(user, token):
        return user
    return None
