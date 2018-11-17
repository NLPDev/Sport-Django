from rest_api.tests import ApiTests
from datetime import timedelta, date
from django.core.urlresolvers import reverse_lazy
from rest_framework import status
from multidb_account.constants import USER_TYPE_COACH
from multidb_account.team.models import Team


class PreCompetitionTests(ApiTests):

    def test_create_list_update_pre_competition(self):
        url = reverse_lazy('rest_api:user-precompetitions', kwargs={'uid': self.athlete_ca.id})
        auth = 'JWT {}'.format(self.athlete_ca.token)
        localized_db = self.athlete_ca.country

        date_future = date.today() + timedelta(days=1)
        date_past = date.today() + timedelta(days=-1)

        # Athlete self create a pre_competition without team
        wrong_date_data = {
            "goal": "goal_1",
            "title": "pre_competition_1",
            "date": date_past,
            "stress": 1,
            "fatigue": 3,
            "hydration": 4,
            "injury": 2,
            "weekly_load": 3
        }
        response = self.client.post(url, wrong_date_data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        wrong_stress_data = {
            "goal": "goal_1",
            "title": "pre_competition_1",
            "date": date_future,
            "stress": 7,
            "fatigue": 3,
            "hydration": 4,
            "injury": 2,
            "weekly_load": 3
        }
        response = self.client.post(url, wrong_stress_data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = {"goal": "goal_1",
                "title": "precompetition_1",
                "date": date_future,
                "stress": 1,
                "fatigue": 3,
                "hydration": 4,
                "injury": 2,
                "weekly_load": 3
                }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for item in data.items():
            self.assertEqual(response.data.get(item), data.get(item))
        self.assertEqual(response.data.get('team_id'), None)
        self.assertEqual(response.data.get('athlete_id'), self.athlete_ca.id)

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in data.items():
            self.assertEqual(response.data[0].get(item), data.get(item))
        self.assertEqual(response.data[0].get('team_id'), None)
        self.assertEqual(response.data[0].get('athlete_id'), self.athlete_ca.id)

        # Athlete self create a pre_competition with a team
        random_coach = self.create_random_user(country='ca', user_type=USER_TYPE_COACH)
        # create dummy team
        resp = self.create_team(owner=random_coach, name='team_1')
        team = Team.objects.using(localized_db).get(id=resp.data['id'])
        data.update({'team_id': team.id})

        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        # athlete is not a team member HTTP_400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        team.athletes.add(self.athlete_ca.athleteuser)
        # athlete is team member HTTP_201
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pre_com_id = response.data.get('id')
        for item in data.items():
            self.assertEqual(response.data.get(item), data.get(item))
        self.assertEqual(response.data.get('athlete_id'), self.athlete_ca.id)

        # connected coach can list pre_competition
        auth = 'JWT {}'.format(random_coach.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        random_coach_2 = self.create_random_user(country='ca', user_type=USER_TYPE_COACH)
        # Non-connected coach can NOT list pre_competition
        auth = 'JWT {}'.format(random_coach_2.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # UPDATE
        data_updated = {"goal": "goal_100",
                        "title": "precompetition_100",
                        "date": date_future,
                        "stress": 4,
                        "fatigue": 4,
                        "hydration": 2,
                        "injury": 1,
                        "weekly_load": 2
                        }
        url = reverse_lazy('rest_api:user-precompetition-detail', kwargs={'uid': self.athlete_ca.id,
                                                                          'pcid': pre_com_id})
        auth = 'JWT {}'.format(self.athlete_ca.token)
        response = self.client.put(url, data_updated, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in data_updated.items():
            self.assertEqual(response.data.get(item), data_updated.get(item))
        self.assertEqual(response.data.get('athlete_id'), self.athlete_ca.id)

        # Connected coach tries to update = Forbidden
        auth = 'JWT {}'.format(random_coach.token)
        response = self.client.put(url, data_updated, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # LIST DETAIL
        auth = 'JWT {}'.format(self.athlete_ca.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in data_updated.items():
            self.assertEqual(response.data.get(item), data_updated.get(item))
        self.assertEqual(response.data.get('athlete_id'), self.athlete_ca.id)

        # Connected coach tries to list detail = authorized
        auth = 'JWT {}'.format(random_coach.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in data_updated.items():
            self.assertEqual(response.data.get(item), data_updated.get(item))
        self.assertEqual(response.data.get('athlete_id'), self.athlete_ca.id)

        # Non connected coach tries to list detail = Forbidden
        auth = 'JWT {}'.format(random_coach_2.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
