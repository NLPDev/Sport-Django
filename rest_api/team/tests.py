from unittest import mock
from datetime import timedelta, date

from django.core.urlresolvers import reverse_lazy
from rest_framework import status

from rest_api.tests import ApiTests
from multidb_account.constants import USER_TYPE_COACH, USER_TYPE_ATHLETE
from multidb_account.user.models import AthleteUser, Coaching
from multidb_account.team.models import Team


class TeamTests(ApiTests):

    def create_pre_competition_with_team(self, team, goal, title, date, athlete: AthleteUser):
        team.athletes.add(athlete)
        url = reverse_lazy('rest_api:user-precompetitions', kwargs={'uid': athlete.user_id})
        auth = 'JWT {}'.format(athlete.user.token)

        data = {"team_id": team.id,
                "goal": goal,
                "title": title,
                "date": date,
                "stress": 1,
                "fatigue": 2,
                "hydration": 3,
                "injury": 4,
                "weekly_load": 4
                }
        return self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)

    def test_create_team(self):
        """
        Ensure we can create a new team.
        """
        auth = 'JWT {}'.format(self.coach_ca.token)
        url = reverse_lazy('rest_api:teams')
        data = {
            'name': 'my_team',
            'status': 'active',
            'tagline': 'team_tagline',
            'season': '2018',
            'location': 'Toronto',
            'owner_id': self.coach_ca.id,
            'sport_id': 3,
            'is_private': True,
            'organisation_id': self.org_ca.organisation.id,
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        team_id = response.data.get('id')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key, value in data.items():
            self.assertEqual(response.data.get(key), value)

        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.coach_ca.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        got_team = response.data.get('team_ownerships')[0]
        self.assertEqual(got_team.get('id'), team_id)
        self.assertEqual(got_team.get('sport_id'), data.get('sport_id'))
        self.assertEqual(got_team.get('name'), data.get('name'))
        self.assertEqual(got_team.get('tagline'), data.get('tagline'))
        self.assertEqual(got_team.get('season'), data.get('season'))
        self.assertEqual(got_team.get('is_private'), data.get('is_private'))
        self.assertEqual(got_team.get('organisation_id'), data.get('organisation_id'))

    def test_create_list_update_team(self):
        """
        Ensure we can create and update new team.
        """
        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:teams')
        data = {'name': 'my_team', 'status': 'active', 'tagline': 'team_tagline', 'season': '2018',
                'location': 'Toronto', 'owner_id': self.coach_us.id, 'sport_id': 3}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key, value in data.items():
            self.assertEqual(response.data.get(key), value)

        url = reverse_lazy('rest_api:team-detail', kwargs={'tid': response.data.get('id')})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key, value in data.items():
            self.assertEqual(response.data.get(key), value)

        update_data = {'name': 'my_team_updated', 'status': 'archived', 'tagline': 'team_tagline_updated',
                       'season': '2019', 'location': 'Montreal'}
        response = self.client.put(url, update_data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key, value in update_data.items():
            self.assertEqual(response.data.get(key), value)
        self.assertEqual(response.data.get('owner_id'), data.get('owner_id'))
        self.assertEqual(response.data.get('sport_id'), data.get('sport_id'))

    def test_team_permissions(self):
        """
        Validate team permissions.
        """
        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:teams')
        data = {'name': 'my_team2', 'status': 'active', 'tagline': 'team_tagline', 'season': '2018',
                'location': 'Toronto', 'owner_id': self.coach_us.id, 'sport_id': 3}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key, value in data.items():
            self.assertEqual(response.data.get(key), value)

        url = reverse_lazy('rest_api:team-detail', kwargs={'tid': response.data.get('id')})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key, value in data.items():
            self.assertEqual(response.data.get(key), value)

        # check non team member access is forbidden
        auth = 'JWT {}'.format(self.athlete_us.token)
        update_data = {'name': 'my_team2_updated', 'status': 'archived', 'tagline': 'team_tagline_updated',
                       'season': '2019', 'location': 'Montreal'}
        response = self.client.put(url, update_data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_list_team_assessments(self):
        localized_db = self.coach_us.country

        # Create a team
        response = self.create_team(self.coach_us)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.using(localized_db).get(id=response.data['id'])

        # Invite athlete by coach to a valid team
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email text'
            response = self.invite_users(requester=self.coach_us, recipient=self.athlete_us, team_id=team.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token = mock_render_to_string.call_args_list[0][0][1]['token']

        # Confirm the invite
        response = self.confirm_invite(token=token, confirmer=self.athlete_us)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that recipient is now a part of the team
        self.assertIn(self.athlete_us.athleteuser, team.athletes.using(localized_db).all())

        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:team-assessments', kwargs={'tid': team.id})

        # Check Coach can assess an athlete team member
        # 4 stars type
        data1 = [{"assessment_id": 1, "assessed_id": self.athlete_us.id, "value": 1},
                 {"assessment_id": 1, "assessed_id": self.athlete_us.id, "value": 2},
                 {"assessment_id": 2, "assessed_id": self.athlete_us.id, "value": 2}]
        response = self.client.post(url, data1, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('assessed_id'), self.athlete_us.id)
            self.assertEqual(assessment.get('assessor_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessment_id'), data1[inc].get('assessment_id'))
            self.assertEqual(assessment.get('team_id'), team.id)
            self.assertEqual(int(float(assessment.get('value'))), int(float(data1[inc].get('value'))))
            inc += 1

        # Check team-assessments-average: average values per team
        url = reverse_lazy('rest_api:team-assessments-average', kwargs={'tid': team.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        gen_phys = next(x for x in response.data if x['name'] == 'General-Physical')
        fms = next(x for x in gen_phys['childs'] if x['name'] == 'Fundamental Movement Skills')

        got_id_1_value = next(x for x in fms['childs'] if x[0]['assessment_id'] == 1)
        self.assertEqual(len(got_id_1_value), 1)  # 1 avg value instead of 2 original values
        self.assertEqual(float(got_id_1_value[0]['value']), 1.5)  # (1 + 2) / 2

        # Create second athlete
        athlete_us_2 = self.create_random_user(country=self.coach_us.country, user_type=USER_TYPE_ATHLETE)

        # Invite athlete by coach to a valid team
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email text'
            response = self.invite_users(requester=self.coach_us, recipient=athlete_us_2, team_id=team.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token = mock_render_to_string.call_args_list[0][0][1]['token']

        # Confirm the invite
        response = self.confirm_invite(token=token, confirmer=athlete_us_2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that recipient is now a part of the team
        self.assertIn(athlete_us_2.athleteuser, team.athletes.using(localized_db).all())

        # 4 stars type
        data2 = [{"assessment_id": 3, "assessed_id": athlete_us_2.id, "value": 3},
                 {"assessment_id": 4, "assessed_id": athlete_us_2.id, "value": 4}]
        url = reverse_lazy('rest_api:team-assessments', kwargs={'tid': team.id})
        response = self.client.post(url, data2, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('assessed_id'), athlete_us_2.id)
            self.assertEqual(assessment.get('assessor_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessment_id'), data2[inc].get('assessment_id'))
            self.assertEqual(assessment.get('team_id'), team.id)
            self.assertEqual(int(float(assessment.get('value'))), int(float(data2[inc].get('value'))))
            inc += 1

        # GET
        response = self.client.get(url, {'latest': ''}, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = [{"assessment_id": 2, "assessed_id": self.athlete_us.id, "value": 2},
                         {"assessment_id": 4, "assessed_id": athlete_us_2.id, "value": 4}]
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('assessed').get('id'), expected_data[inc].get('assessed_id'))
            self.assertEqual(assessment.get('assessor_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessment_id'), expected_data[inc].get('assessment_id'))
            self.assertEqual(assessment.get('team_id'), team.id)
            self.assertEqual(int(float(assessment.get('value'))), int(float(expected_data[inc].get('value'))))
            inc += 1

    def test_revoke_from_team(self):
        localized_db = self.coach_ca.country
        team_owner = self.coach_ca

        # Create a team with members
        response = self.create_team(owner=team_owner)
        team = Team.objects.using(localized_db).get(id=response.data['id'])

        team.athletes.add(self.athlete_ca.athleteuser)
        team.coaches.add(self.coach_ca.coachuser)

        self.assertIn(self.athlete_ca.athleteuser, team.athletes.using(localized_db).all())
        self.assertIn(self.coach_ca.coachuser, team.coaches.using(localized_db).all())

        # Create another dummy team
        response = self.create_team(owner=team_owner, name='team2')
        team2_id = response.data['id']

        # Create dummy users
        bad_coach = self.create_random_user(country='ca', user_type=USER_TYPE_COACH)
        bad_user = self.create_random_user(country='ca', user_type=USER_TYPE_ATHLETE)

        # Revoke not as a team owner
        response = self.revoke_from_team(revoker=bad_coach, team_id=team.id, revokee_id=self.athlete_ca.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Revoke wrong user
        response = self.revoke_from_team(revoker=self.coach_ca, team_id=team.id, revokee_id=bad_user.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Revoke wrong user #2
        response = self.revoke_from_team(revoker=self.coach_ca, team_id=team.id, revokee_id=0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Revoke from wrong team
        response = self.revoke_from_team(revoker=self.coach_ca, team_id=team2_id, revokee_id=self.athlete_ca.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Revoke from wrong team #2
        response = self.revoke_from_team(revoker=self.coach_ca, team_id=0, revokee_id=self.athlete_ca.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Revoke athlete
        response = self.revoke_from_team(revoker=team_owner, team_id=team.id, revokee_id=self.athlete_ca.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that revokee isn't a part of the team now
        self.assertNotIn(self.athlete_ca, team.athletes.using(localized_db).all())
        self.assertIn(self.coach_ca.coachuser, team.coaches.using(localized_db).all())

        # Revoke coach
        response = self.revoke_from_team(revoker=team_owner, team_id=team.id, revokee_id=self.coach_ca.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that revokee isn't a part of the team now
        self.assertNotIn(self.athlete_ca, team.athletes.using(localized_db).all())
        self.assertNotIn(self.coach_ca.coachuser, team.coaches.using(localized_db).all())

    def test_self_revoke_from_team(self):
        localized_db = self.coach_ca.country
        team_owner = self.coach_ca

        # Create a team with members
        response = self.create_team(owner=team_owner)
        team = Team.objects.using(localized_db).get(id=response.data['id'])

        team.athletes.add(self.athlete_ca.athleteuser)
        team.coaches.add(self.coach_ca.coachuser)

        self.assertIn(self.athlete_ca.athleteuser,
                      team.athletes.using(localized_db).all())
        self.assertIn(self.coach_ca.coachuser,
                      team.coaches.using(localized_db).all())

        # Create dummy users
        bad_user = self.create_random_user(country='ca',
                                           user_type=USER_TYPE_ATHLETE)

        team.athletes.add(self.athlete_ca.athleteuser)

        # Self revoke not as a coach
        response = self.revoke_from_team(revoker=bad_user,
                                         team_id=team.id,
                                         revokee_id=self.athlete_ca.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Self revoke not as a coach
        response = self.revoke_from_team(revoker=self.athlete_ca,
                                         team_id=team.id,
                                         revokee_id=self.athlete_ca.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg=response.json())

        # Check that athlete isn't a part of the team now
        self.assertNotIn(self.athlete_ca, team.athletes.using(localized_db).all())

    def test_list_team_pre_competition(self):
        localized_db = 'ca'
        athletes = [self.create_random_user(country=localized_db, user_type=USER_TYPE_ATHLETE),
                    self.create_random_user(country=localized_db, user_type=USER_TYPE_ATHLETE),
                    self.create_random_user(country=localized_db, user_type=USER_TYPE_ATHLETE)]

        random_coach = self.create_random_user(country='ca', user_type=USER_TYPE_COACH)
        # create dummy team
        resp = self.create_team(owner=random_coach, name='team_precompetition')
        team = Team.objects.using(localized_db).get(id=resp.data['id'])

        first_pre_com = []
        last_pre_com = []
        for index in [0, 1, 2]:
            first_pre_com.append(self.create_pre_competition_with_team(team, "fpr_g_" + str(index),
                                                                       "fpr_t_" + str(index),
                                                                       date.today() + timedelta(days=index + 1),
                                                                       athletes[index].athleteuser))
            last_pre_com.append(self.create_pre_competition_with_team(team, "lpr_g_" + str(index),
                                                                      "lpr_t_" + str(index),
                                                                      date.today() + timedelta(days=index + 4),
                                                                      athletes[index].athleteuser))

        url = reverse_lazy('rest_api:team-precompetitions', kwargs={'tid': team.id})
        auth = 'JWT {}'.format(random_coach.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for index in [0, 1, 2]:
            for key in ['team_id', 'title', 'goal', 'date', 'stress', 'fatigue', 'hydration', 'injury', 'weekly_load']:
                self.assertEqual(response.data[index].get(key), last_pre_com[index].data.get(key))

    def test_athlete_linked_team_coaches(self):
        localized_db = self.coach_ca.country
        our_team_coach = self.coach_ca
        alien_coach = self.create_random_user(country=localized_db, user_type=USER_TYPE_COACH)
        our_coach_2 = self.create_random_user(country=localized_db, user_type=USER_TYPE_COACH)

        # Create our_team with members
        response = self.create_team(owner=our_team_coach)
        our_team = Team.objects.using(localized_db).get(id=response.data['id'])
        our_team.athletes.add(self.athlete_ca.athleteuser)
        our_team.coaches.add(self.coach_ca.coachuser)

        # Create alien_team with members
        response = self.create_team(owner=our_team_coach)
        alien_team = Team.objects.using(localized_db).get(id=response.data['id'])
        alien_team.coaches.add(alien_coach.coachuser)

        # Add direct coach connection
        Coaching.objects.using(localized_db).create(athlete=self.athlete_ca.athleteuser, coach=our_coach_2.coachuser)

        # GET linked users => only direct connections
        auth = 'JWT {}'.format(self.athlete_ca.token)
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.athlete_ca.athleteuser.pk})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['linked_users']), 1)

        got_coach = response.data['linked_users'][0]
        self.assertEqual(got_coach['id'], our_coach_2.pk)
        self.assertEqual(got_coach['teams'], [])
