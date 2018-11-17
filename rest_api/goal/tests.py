from datetime import timedelta, datetime
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from rest_framework import status

from multidb_account.constants import USER_TYPE_COACH
from multidb_account.goal.models import Goal
from multidb_account.user.models import Coaching

from rest_api.tests import ApiTests

UserModel = get_user_model()


class GoalTests(ApiTests):

    def test_own_goals_crud(self):
        user = self.coach_ca
        user2 = self.athlete_ca
        auth = 'JWT {}'.format(user.token)
        auth2 = 'JWT {}'.format(user2.token)
        url = reverse_lazy('rest_api:goal-list')

        # Create a goal by user1
        data = {
            'description': '...',
            'achieve_by': (datetime.utcnow() + timedelta(weeks=4)).date(),
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        goal = Goal.objects.using(user.country).get(pk=response.data['id'])
        self.assertEqual(goal.user, user)
        self.assertEqual(goal.description, data['description'])
        self.assertEqual(goal.achieve_by, data['achieve_by'])

        # Create a goal by user2
        data = {
            'description': '...#2',
            'achieve_by': (datetime.utcnow() + timedelta(weeks=2)).date(),
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth2)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        goal2 = Goal.objects.using(user2.country).get(pk=response.data['id'])
        self.assertEqual(goal2.user, user2)

        # GET all goals of user1
        url = reverse_lazy('rest_api:goal-list')

        # GET goal of user2 by user1: 404
        url2 = reverse_lazy('rest_api:goal-detail', kwargs={'pk': goal2.pk})
        response = self.client.get(url2, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # GET goal of user1
        url = reverse_lazy('rest_api:goal-detail', kwargs={'pk': goal.pk})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], goal.id)
        self.assertEqual(response.data['user'], user.id)
        self.assertEqual(response.data['description'], goal.description)
        self.assertEqual(response.data['achieve_by'], str(goal.achieve_by))
        self.assertEqual(response.data['is_achieved'], goal.is_achieved)

        # PUT
        old_description = goal.description
        old_is_achieved = goal.is_achieved
        description = 'f3red332de'
        data = {'description': description, 'is_achieved': True}
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        goal.refresh_from_db()
        self.assertEqual(goal.description, description)
        self.assertNotEqual(goal.description, old_description)
        self.assertNotEqual(goal.is_achieved, old_is_achieved)

        # PATCH
        old_description = goal.description
        old_is_achieved = goal.is_achieved
        description = 'dsf32sf23f2'
        data = {'description': description, 'is_achieved': 0}
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        goal.refresh_from_db()
        self.assertEqual(goal.description, description)
        self.assertNotEqual(goal.description, old_description)
        self.assertNotEqual(goal.is_achieved, old_is_achieved)

        # PUT incorrect goal (of another owner)
        url2 = reverse_lazy('rest_api:goal-detail', kwargs={'pk': goal2.pk})

        description = 'f3red332de'
        data = {'description': description}
        response = self.client.put(url2, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # PATCH incorrect goal (of another owner)
        response = self.client.patch(url2, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE incorrect goal (of another owner)
        response = self.client.delete(url2, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE correct goal (ours)
        response = self.client.delete(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_other_user_goals(self):
        user = self.coach_ca
        user2 = self.athlete_ca
        user_alien = self.create_random_user(country='ca', user_type=USER_TYPE_COACH)
        auth = 'JWT {}'.format(user.token)
        auth2 = 'JWT {}'.format(user2.token)
        auth_alien = 'JWT {}'.format(user_alien.token)
        url = reverse_lazy('rest_api:goal-list')

        # Create a goal by user1
        data = {
            'description': '...',
            'achieve_by': (datetime.utcnow() + timedelta(weeks=4)).date(),
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        goal = Goal.objects.using(user.country).get(pk=response.data['id'])

        # Create a goal by user2
        data = {
            'description': '...#2',
            'achieve_by': (datetime.utcnow() + timedelta(weeks=2)).date(),
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth2)
        goal2 = Goal.objects.using(user2.country).get(pk=response.data['id'])

        # GET goals of user2 by user1 -> FAIL: not connected
        url = reverse_lazy('rest_api:user-goals', kwargs={'uid': user2.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # GET goals of user1 by user2 -> FAIL: not connected
        url = reverse_lazy('rest_api:user-goals', kwargs={'uid': user.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth2)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # GET goals of user1 by alien_user -> FAIL: not connected
        url = reverse_lazy('rest_api:user-goals', kwargs={'uid': user.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth_alien)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Connect user1 & user2 via Coaching
        Coaching.objects.using(user.country).create(coach=user.coachuser, athlete=user2.athleteuser)

        # GET goals of user2 by user1 -> FAIL: not connected
        url = reverse_lazy('rest_api:user-goals', kwargs={'uid': user2.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['id'], goal2.id)

        # GET goals of user1 by user2 -> FAIL: not connected
        url = reverse_lazy('rest_api:user-goals', kwargs={'uid': user.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['id'], goal.id)

        # GET goals of user1 by alien_user -> FAIL: still not connected
        url = reverse_lazy('rest_api:user-goals', kwargs={'uid': user.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth_alien)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # PUT -> FAIL
        response = self.client.put(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # PATCH -> FAIL
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # DELETE -> FAIL
        response = self.client.delete(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # GET goals of bad user id -> FAIL
        url = reverse_lazy('rest_api:user-goals', kwargs={'uid': 999})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
