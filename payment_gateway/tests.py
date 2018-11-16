from datetime import timedelta

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from django.utils import timezone
from rest_framework import status

from multidb_account.constants import USER_TYPE_ATHLETE
from rest_api.tests import ApiTests

UserModel = get_user_model()


class PaymentTests(ApiTests):
    def test_disable_users(self):
        # Setup users
        customer = self.athlete_ca.athleteuser.customer
        customer2 = self.create_random_user(country=self.athlete_ca.country, user_type=USER_TYPE_ATHLETE) \
            .athleteuser.customer
        customer3 = self.create_random_user(country=self.athlete_ca.country, user_type=USER_TYPE_ATHLETE) \
            .athleteuser.customer

        customer.payment_status = 'grace_period'
        customer2.payment_status = 'grace_period'
        customer3.payment_status = 'grace_period'

        customer2.grace_period_end = timezone.now() - timedelta(days=1)
        customer3.grace_period_end = timezone.now() + timedelta(days=1)

        customer.save(update_fields=('payment_status',))
        customer2.save(update_fields=('grace_period_end', 'payment_status'))
        customer3.save(update_fields=('grace_period_end', 'payment_status'))

        url = reverse_lazy('rest_api:disable-expired-customers')

        # Wrong data
        data = {'token': ''}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        data = {}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        data = {'token': 'wrong token'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Valid data
        data = {'token': django_settings.DISABLE_EXPIRED_CUSTOMERS_TOKEN}

        # Wrong methods
        response = self.client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Valid POST
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        customer.refresh_from_db()
        customer2.refresh_from_db()
        customer3.refresh_from_db()

        self.assertEqual(customer.payment_status, 'grace_period')
        self.assertEqual(customer2.payment_status, 'locked_out')
        self.assertEqual(customer3.payment_status, 'grace_period')

    def test_payment_not_needed(self):
        customer = self.athlete_ca.athleteuser.customer
        auth = 'JWT {}'.format(self.athlete_ca.token)
        url = reverse_lazy('rest_api:payment', kwargs={'uid': customer.athlete.user.id})
        self.assertEqual(customer.payment_status, 'no_card')

        # POST with a not_needed payment plan
        data = {'token': None, 'plan': 'not_needed'}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        customer.refresh_from_db()
        self.assertEqual(customer.payment_status, 'not_needed')
