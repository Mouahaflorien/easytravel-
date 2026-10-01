from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.core.exceptions import ValidationError
from accounts.models import User
from accounts.validators import (
    validate_cameroon_phone, 
    validate_clean_email, 
    validate_identity_info,
    validate_passenger_name
)
from accounts.services.email_service import (
    send_account_activation_email, 
    verify_activation_token,
    generate_activation_link
)

class AccountsValidationTest(TestCase):
    def test_phone_validation_cameroon(self):
        # Orange Cameroun (69x, 655-659)
        self.assertEqual(validate_cameroon_phone("699001122"), "+237 699 001 122")
        self.assertEqual(validate_cameroon_phone("655443322"), "+237 655 443 322")
        # MTN Cameroun (67x, 68x, 650-654)
        self.assertEqual(validate_cameroon_phone("+237677001122"), "+237 677 001 122")
        self.assertEqual(validate_cameroon_phone("00237 680 11 22 33"), "+237 680 112 233")
        # Nexttel (66x) & Camtel (62x)
        self.assertEqual(validate_cameroon_phone("661234567"), "+237 661 234 567")
        self.assertEqual(validate_cameroon_phone("620123456"), "+237 620 123 456")
        # Fixes nationaux (222, 233, etc.)
        self.assertEqual(validate_cameroon_phone("222201122"), "+237 222 20 11 22")

    def test_phone_validation_international(self):
        # Format France (+33)
        self.assertEqual(validate_cameroon_phone("+33612345678"), "+33 6 12 34 56 78")
        # Format Allemagne (+49)
        self.assertEqual(validate_cameroon_phone("+4917635321633"), "+49 176 3532 1633")
        # Format International générique (Gabon, USA, etc.)
        self.assertTrue(validate_cameroon_phone("+24162123456").startswith("+241"))
        self.assertTrue(validate_cameroon_phone("+12025550199").startswith("+1"))

    def test_invalid_phone(self):
        # Répétitions / numéros bidons
        with self.assertRaises(ValidationError):
            validate_cameroon_phone("666666666")
        with self.assertRaises(ValidationError):
            validate_cameroon_phone("600000000")
        with self.assertRaises(ValidationError):
            validate_cameroon_phone("+33111111111")
        # Préfixe inexistant au Cameroun (ex: 61x ou 55x)
        with self.assertRaises(ValidationError):
            validate_cameroon_phone("611001122")
        with self.assertRaises(ValidationError):
            validate_cameroon_phone("555001122")
        # Trop court
        with self.assertRaises(ValidationError):
            validate_cameroon_phone("12345")

    def test_passenger_name_validation(self):
        # Noms valides
        self.assertEqual(validate_passenger_name("Kamgaing Jean-Paul"), "Kamgaing Jean-Paul")
        self.assertEqual(validate_passenger_name("Paul Biya"), "Paul Biya")
        self.assertEqual(validate_passenger_name("Marie-claire Ngo Ndjock"), "Marie-Claire Ngo Ndjock")

        # Noms invalides
        with self.assertRaises(ValidationError):
            validate_passenger_name("Paul")  # 1 seul mot
        with self.assertRaises(ValidationError):
            validate_passenger_name("Passager Clandestin")  # Terme interdit
        with self.assertRaises(ValidationError):
            validate_passenger_name("Test User")  # Mots interdits
        with self.assertRaises(ValidationError):
            validate_passenger_name("Paul 123")  # Chiffres interdits
        with self.assertRaises(ValidationError):
            validate_passenger_name("aaaa bbbb")  # Répétitions

    def test_identity_validation(self):
        # CNI valide
        t, num = validate_identity_info("CNI", "  102938475  ")
        self.assertEqual(t, "CNI")
        self.assertEqual(num, "102938475")
        
        t, num = validate_identity_info("CNI", "CE10293847")
        self.assertEqual(num, "CE10293847")

        # Passeport valide (lettres et chiffres)
        t, num = validate_identity_info("PASSPORT", "A1234567")
        self.assertEqual(t, "PASSPORT")
        self.assertEqual(num, "A1234567")

        t, num = validate_identity_info("PASSPORT", "09AA12345")
        self.assertEqual(num, "09AA12345")

        # Récépissé valide
        t, num = validate_identity_info("RECEIPT", "REC20261234")
        self.assertEqual(t, "RECEIPT")

        # Invalides
        with self.assertRaises(ValidationError):
            validate_identity_info("PERMIS", "12345")  # Type invalide
        with self.assertRaises(ValidationError):
            validate_identity_info("CNI", "12")  # Trop court
        with self.assertRaises(ValidationError):
            validate_identity_info("CNI", "12345678")  # Séquence triviale
        with self.assertRaises(ValidationError):
            validate_identity_info("CNI", "000000000")  # Répétitif
        with self.assertRaises(ValidationError):
            validate_identity_info("CNI", "CNIFRAUD7788")  # Terme interdit
        with self.assertRaises(ValidationError):
            validate_identity_info("PASSPORT", "12345678")  # Pas de lettres


class AccountEmailActivationTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_registration_creates_inactive_user_and_sends_email(self):
        mail.outbox = []
        response = self.client.post(reverse('accounts:register'), {
            'full_name': 'Mbarga Joseph',
            'email': 'mbarga.joseph@mslogitech.cm',
            'phone': '699112233',
            'id_type': 'CNI',
            'id_number': '102938475',
            'password': 'SecurePassword2026!',
            'password_confirm': 'SecurePassword2026!'
        })

        # Doit rediriger vers la page d'attente d'activation
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:activation_pending'), response.url)

        # L'utilisateur doit exister en base de données avec is_active=False
        user = User.objects.get(email='mbarga.joseph@mslogitech.cm')
        self.assertFalse(user.is_active)
        self.assertEqual(user.first_name, 'Mbarga')
        self.assertEqual(user.last_name, 'Joseph')
        self.assertEqual(user.id_type, 'CNI')
        self.assertEqual(user.id_number, '102938475')

        # Un email doit avoir été envoyé
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Activez votre compte voyageur", mail.outbox[0].subject)
        self.assertIn(user.email, mail.outbox[0].to)

    def test_activation_link_activates_account(self):
        # Création d'un utilisateur inactif
        user = User.objects.create_user(
            username='jean_inactive',
            email='jean.inactive@mslogitech.cm',
            password='TestPassword123!',
            first_name='Jean',
            last_name='Ngo',
            is_active=False
        )
        self.assertFalse(user.is_active)

        # Génération du lien d'activation
        activation_url = generate_activation_link(None, user)
        # Extraire uidb64 et token de l'url
        parts = activation_url.rstrip('/').split('/')
        token = parts[-1]
        uidb64 = parts[-2]

        # Visiter le lien d'activation
        response = self.client.get(reverse('accounts:activate_account', kwargs={'uidb64': uidb64, 'token': token}))
        self.assertEqual(response.status_code, 302)

        # Le compte doit être maintenant actif
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_inactive_user_login_detection(self):
        User.objects.create_user(
            username='inactive_login_user',
            email='inactive.login@mslogitech.cm',
            password='MySecretPassword123!',
            is_active=False
        )

        response = self.client.post(reverse('accounts:login'), {
            'action_login': '1',
            'identifier': 'inactive.login@mslogitech.cm',
            'password': 'MySecretPassword123!'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['login_error'], 'inactive_account')
        self.assertEqual(response.context['unactivated_email'], 'inactive.login@mslogitech.cm')
