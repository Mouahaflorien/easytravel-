from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from agencies.models import Agency, AuditAnomaly, AgencyNotification
from agencies.context_processors import get_current_agency, agency_context

User = get_user_model()

class AgencyTenantTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user1 = User.objects.create_user(username='boss1', password='pw', email='boss1@test.cm')
        self.user2 = User.objects.create_user(username='boss2', password='pw', email='boss2@test.cm')
        self.agency1 = Agency.objects.create(name='FINEX TEST', owner=self.user1)
        self.agency2 = Agency.objects.create(name='GENERAL TEST', owner=self.user2)

    def test_strict_tenancy_isolation(self):
        req1 = self.factory.get('/portail-agence/dashboard/')
        req1.user = self.user1
        self.assertEqual(get_current_agency(req1), self.agency1)

        req2 = self.factory.get('/portail-agence/dashboard/')
        req2.user = self.user2
        self.assertEqual(get_current_agency(req2), self.agency2)

    def test_anomaly_and_notification_creation(self):
        anomaly = AuditAnomaly.objects.create(
            agency=self.agency1,
            category='price_mismatch',
            severity='high',
            title='Test Anomalie Tarif',
            description='Tarif hors grille'
        )
        notif = AgencyNotification.objects.create(
            agency=self.agency1,
            anomaly=anomaly,
            title='Alerte Tarif',
            message='Détail'
        )
        self.assertEqual(self.agency1.anomalies.count(), 1)
        self.assertEqual(self.agency1.notifications.count(), 1)
        self.assertFalse(notif.is_read)
