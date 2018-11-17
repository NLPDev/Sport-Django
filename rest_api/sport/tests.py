from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from rest_framework import status
from rest_api.tests import ApiTests

UserModel = get_user_model()


class SportTests(ApiTests):

    def test_update_athlete_sports(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)
        data = [{"sport_id": 1, "is_displayed": True, "is_chosen": True},
                {"sport_id": 3, "is_displayed": True, "is_chosen": False},
                {"sport_id": 5, "is_displayed": False, "is_chosen": True}
                ]
        # chosen_sport
        url = reverse_lazy('rest_api:chosen-sports', kwargs={'uid': self.athlete_ca.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inc = 0
        for sport in response.data:
            self.assertEqual(sport.get('id'), data[inc].get('id'))
            self.assertEqual(sport.get('is_displayed'), data[inc].get('is_displayed'))
            self.assertEqual(sport.get('is_chosen'), data[inc].get('is_chosen'))
            inc += 1

    def test_update_coach_sports(self):
        auth = 'JWT {}'.format(self.coach_us.token)
        data = [{"sport_id": 1, "is_displayed": True, "is_chosen": True},
                {"sport_id": 3, "is_displayed": True, "is_chosen": False},
                {"sport_id": 5, "is_displayed": False, "is_chosen": True}
                ]
        # chosen_sport
        url = reverse_lazy('rest_api:chosen-sports', kwargs={'uid': self.coach_us.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inc = 0
        for sport in response.data:
            self.assertEqual(sport.get('id'), data[inc].get('id'))
            self.assertEqual(sport.get('is_displayed'), data[inc].get('is_displayed'))
            self.assertEqual(sport.get('is_chosen'), data[inc].get('is_chosen'))
            inc += 1
