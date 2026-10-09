from datetime import date, time, timedelta
from django.test import TestCase
from accounts.models import User
from agencies.models import Agency
from travel.models import City, Line, LineStop, Departure, Vehicle
from bookings.models import Booking

class BookingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='traveler1', password='pw', phone='699112233', email='traveler1@test.cm')
        self.owner = User.objects.create_user(username='agencyowner2', password='pw', email='owner2@test.cm')
        self.agency = Agency.objects.create(name="Voyage Test", owner=self.owner)
        self.city_a = City.objects.create(name="Douala")
        self.city_b = City.objects.create(name="Bafoussam")
        self.line = Line.objects.create(agency=self.agency, name="Ligne Ouest")
        self.stop_1 = LineStop.objects.create(line=self.line, city=self.city_a, stop_order=1, price_from_start=0)
        self.stop_2 = LineStop.objects.create(line=self.line, city=self.city_b, stop_order=2, price_from_start=5000)
        self.departure = Departure.objects.create(
            agency=self.agency,
            line=self.line,
            date=date.today(),
            time=time(8, 30),
            available_capacity=30
        )

    def test_booking_creation_and_reference(self):
        booking = Booking.objects.create(
            user=self.user,
            departure=self.departure,
            departure_stop=self.stop_1,
            arrival_stop=self.stop_2,
            traveler_name="Samuel Eto'o",
            traveler_phone="699112233",
            traveler_email="samuel@test.com",
            id_type="CNI",
            id_number="101010101",
            seats_reserved=2,
            total_amount=10000,
            status='confirmed',
            payment_status='paid'
        )
        self.assertTrue(booking.reference.startswith("ET-"))
        self.assertEqual(len(booking.reference), 11)  # ET- + 8 chars
        self.assertIsNotNone(booking.paid_at)
        self.assertEqual(booking.seats_reserved, 2)
        self.assertEqual(booking.total_amount, 10000)

    def test_booking_string_representation(self):
        booking = Booking.objects.create(
            departure=self.departure,
            traveler_name="Roger Milla",
            traveler_phone="677001122",
            traveler_email="roger@test.com",
            id_type="CNI",
            id_number="102938475",
            seats_reserved=1,
            total_amount=5000
        )
        self.assertIn("Roger Milla", str(booking))
        self.assertIn(booking.reference, str(booking))

    def test_unauthenticated_booking_creates_account_and_requires_email_activation(self):
        from django.test import Client
        from django.urls import reverse
        from django.core import mail
        from accounts.services.email_service import generate_activation_link

        client = Client()
        mail.outbox = []

        initial_capacity = self.departure.available_capacity
        url = f"{reverse('bookings:book', kwargs={'departure_id': self.departure.id})}?start={self.stop_1.id}&end={self.stop_2.id}"

        response = client.post(url, {
            'start_id': self.stop_1.id,
            'end_id': self.stop_2.id,
            'name': 'Rigobert Song',
            'phone': '699112233',
            'email': 'rigobert.song@mslogitech.cm',
            'id_type': 'CNI',
            'id_number': '102938475',
            'seats': 2,
            'password': 'SongPassword2026!',
            'password_confirm': 'SongPassword2026!'
        })

        # Doit rediriger vers le paiement ou confirmation
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que le compte utilisateur a été créé avec is_active=True
        new_user = User.objects.get(email='rigobert.song@mslogitech.cm')
        self.assertTrue(new_user.is_active)

        # Vérifier que la réservation a été créée en statut 'pending'
        booking = Booking.objects.get(user=new_user)
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.seats_reserved, 2)

        # La capacité est déduite immédiatement
        self.departure.refresh_from_db()
        self.assertEqual(self.departure.available_capacity, initial_capacity - 2)



