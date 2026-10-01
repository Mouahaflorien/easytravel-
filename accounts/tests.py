from django.test import TestCase
from django.core.exceptions import ValidationError
from accounts.models import User
from accounts.validators import validate_cameroon_phone, validate_clean_email, validate_identity_info

class AccountsTest(TestCase):
    def test_phone_validation_cameroon(self):
        # 9 chiffres locaux
        self.assertEqual(validate_cameroon_phone("699001122"), "+237 699 001 122")
        # Format avec indicatif
        self.assertEqual(validate_cameroon_phone("+237677001122"), "+237 677 001 122")
        self.assertEqual(validate_cameroon_phone("00237 655 44 33 22"), "+237 655 443 322")

    def test_phone_validation_international(self):
        # Format France
        self.assertEqual(validate_cameroon_phone("+33612345678"), "+33 6 12 34 56 78")
        # Format Allemagne
        self.assertEqual(validate_cameroon_phone("+4917635321633"), "+49 176 3532 1633")

    def test_invalid_phone(self):
        with self.assertRaises(ValidationError):
            validate_cameroon_phone("12345")
        with self.assertRaises(ValidationError):
            validate_cameroon_phone("555001122")  # Ne commence pas par 6 ou 2

    def test_identity_validation(self):
        t, num = validate_identity_info("CNI", "  10125  ")
        self.assertEqual(t, "CNI")
        self.assertEqual(num, "10125")
        
        with self.assertRaises(ValidationError):
            validate_identity_info("PERMIS", "12345")  # Type invalide
            
        with self.assertRaises(ValidationError):
            validate_identity_info("CNI", "12")  # Trop court
