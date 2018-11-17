from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status

from multidb_account.promocode.models import Promocode
from rest_api.tests import ApiTests

UserModel = get_user_model()


class PromocodeTests(ApiTests):

    def test_promocode(self):
        coach = self.coach_ca
        coach_auth = 'JWT {}'.format(coach.token)
        athlete = self.athlete_ca
        athlete_auth = 'JWT {}'.format(athlete.token)

        # Create promocode
        promo = Promocode.objects.using(athlete.country).create(code='FSD$#$',
                                                                discount=0,
                                                                name='',
                                                                end_date=timezone.now())

        # Create duplicated code
        with transaction.atomic(using=athlete.country):
            with self.assertRaises(IntegrityError):
                Promocode.objects.using(athlete.country).create(code='FSD$#$',
                                                                discount=10,
                                                                name='#2',
                                                                end_date=timezone.now())

        # Validate promo via GET retrieve by coach - Fail
        url = reverse_lazy('rest_api:promocode-detail', kwargs={'code': promo.code})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Validate promo via GET retrieve by athlete - OK
        url = reverse_lazy('rest_api:promocode-detail', kwargs={'code': promo.code})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], promo.code)
        self.assertEqual(response.data['discount'], promo.discount)
