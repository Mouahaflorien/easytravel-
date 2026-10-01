from datetime import date, time, timedelta
from django.test import TestCase
from accounts.models import User
from agencies.models import Agency
from travel.models import City, Line, LineStop, Departure, Vehicle
from bookings.models import Booking

class BookingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='traveler1', password='pw', phone='699112233')
        self.owner = User.objects.create_user(username='agencyowner2', password='pw')
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
            id_number="99887766",
            seats_reserved=1,
            total_amount=5000
        )
        self.assertIn("Roger Milla", str(booking))
        self.assertIn(booking.reference, str(booking))
