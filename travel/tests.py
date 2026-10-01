from datetime import date, time, timedelta
from django.test import TestCase
from accounts.models import User
from agencies.models import Agency
from travel.models import City, Line, LineStop, Departure, Vehicle, Driver

class TravelModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agencyowner', password='pw')
        self.agency = Agency.objects.create(name="Finex Test", owner=self.user)
        self.city_a = City.objects.create(name="Douala")
        self.city_b = City.objects.create(name="Yaoundé")
        self.line = Line.objects.create(agency=self.agency, name="Axe Lourd Littoral-Centre")
        self.stop_1 = LineStop.objects.create(line=self.line, city=self.city_a, stop_order=1, price_from_start=0)
        self.stop_2 = LineStop.objects.create(
            line=self.line, city=self.city_b, stop_order=2, price_from_start=4000,
            duration_from_start=timedelta(hours=4)
        )
        self.vehicle = Vehicle.objects.create(agency=self.agency, vehicle_type="Classique 50", capacity=50)
        self.driver = Driver.objects.create(agency=self.agency, first_name="Jean", last_name="Menga", phone="699001122")
        self.departure = Departure.objects.create(
            agency=self.agency,
            line=self.line,
            vehicle=self.vehicle,
            driver=self.driver,
            date=date.today(),
            time=time(10, 0),
            available_capacity=50
        )

    def test_line_properties(self):
        self.assertEqual(self.line.departure_city, self.city_a)
        self.assertEqual(self.line.arrival_city, self.city_b)
        self.assertEqual(self.line.get_duration(), timedelta(hours=4))

    def test_departure_capacities(self):
        self.assertEqual(self.departure.available_capacity, 50)
        self.assertEqual(self.departure.total_capacity, 50)
        self.assertEqual(self.departure.booked_seats, 0)
        self.assertEqual(self.departure.occupancy_rate, 0.0)

    def test_driver_representation(self):
        self.assertEqual(self.driver.full_name, "Jean Menga")
        self.assertIn("Jean Menga", str(self.driver))
