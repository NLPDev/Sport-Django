from collections import namedtuple
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from rest_framework import status
from rest_framework.test import APITestCase
from typing import List

from multidb_account.constants import USER_TYPE_ATHLETE, USER_TYPE_COACH, USER_TYPE_ORG
from multidb_account.user.models import CoachUser, AthleteUser, Organisation
from multidb_account.assessment.models import Assessor, Assessed
from multidb_account.sport.models import Sport, ChosenSport
from payment_gateway.models import Customer

from rest_api.utils import generate_user_jwt_token

UserModel = get_user_model()


class ApiTests(APITestCase):
    multi_db = True

    user_counter = 0

    def setUp(self):
        self.profile_items = ["email", "country", "user_type", "province_or_state", "city", "first_name", "last_name",
                              "date_of_birth", "newsletter", "terms_conditions", "measuring_system", "tagline",
                              ]
        self.athlete_extended_profile_items = self.profile_items + ['referral_code', 'athlete_terms_conditions']

        self.user_common_data = {"province_or_state": "Ontario",
                                 "city": "Toronto",
                                 "first_name": "f_test",
                                 "last_name": "l_test",
                                 "date_of_birth": "1984-02-03",
                                 "newsletter": True,
                                 "terms_conditions": True,
                                 "measuring_system": "metric",
                                 "tagline": "My tagline",
                                 }

        self.athlete_extended_data = {'referral_code': 'RC', 'athlete_terms_conditions': False}

        self.athlete = self.create_random_user(country='default', user_type=USER_TYPE_ATHLETE)
        self.athlete_ca = self.create_random_user(country='ca', user_type=USER_TYPE_ATHLETE)
        self.athlete_us = self.create_random_user(country='us', user_type=USER_TYPE_ATHLETE)
        self.coach = self.create_random_user(country='default', user_type=USER_TYPE_COACH)
        self.coach_ca = self.create_random_user(country='ca', user_type=USER_TYPE_COACH)
        self.coach_us = self.create_random_user(country='us', user_type=USER_TYPE_COACH)
        self.org_ca = self.create_random_user(country='ca', user_type=USER_TYPE_ORG)

    def create_random_user(self, country, user_type, organisation_name=''):

        self.__class__.user_counter += 1
        counter = self.__class__.user_counter
        user = UserModel.objects.db_manager(country).create_user(
            email="{}{}@test.com".format(user_type, counter),
            country=country,
            password='password',
        )
        user.user_type = user_type
        user.province_or_state = self.user_common_data.get('province_or_state')
        user.city = self.user_common_data.get('city')
        user.first_name = self.user_common_data.get('first_name')
        user.last_name = self.user_common_data.get('last_name')
        user.date_of_birth = self.user_common_data.get('date_of_birth')
        user.newsletter = self.user_common_data.get('newsletter')
        user.terms_conditions = self.user_common_data.get('terms_conditions')
        user.tagline = self.user_common_data.get('tagline')
        user.measuring_system = self.user_common_data.get('measuring_system')

        # create default user's chosen sport and set value if if specified in the validated_data
        for default_sport in Sport.objects.using(user.country).filter(is_available=True):
            ChosenSport.objects.using(user.country).create(user_id=user.id, sport_id=default_sport.id,
                                                           is_chosen=False, is_displayed=False)

        # Add the user model extensions based on the user_type
        if user_type == USER_TYPE_ATHLETE:
            at = AthleteUser(user=user)
            at.referral_code = self.athlete_extended_data.get('referral_code')
            at.athlete_terms_conditions = self.athlete_extended_data.get('athlete_terms_conditions')
            at.athlete_terms_conditions = False
            at.save(using=user.country)
            cu = Customer(athlete=at)
            cu.save(using=user.country)
            assed = Assessed(id=at.user_id, athlete=at)
            assed.save(using=user.country)
            assor = Assessor(id=at.user_id, athlete=at)
            assor.save(using=user.country)

        elif user_type == USER_TYPE_COACH:
            co = CoachUser(user=user)
            co.save(using=user.country)
            assed = Assessed(id=co.user_id, coach=co)
            assed.save(using=user.country)
            assor = Assessor(id=co.user_id, coach=co)
            assor.save(using=user.country)

        elif user_type == USER_TYPE_ORG:
            co = Organisation(name=organisation_name)
            co.save(using=user.country)
            co.login_users.add(user)

        user.save(using=user.country)
        user.token = generate_user_jwt_token(user)
        return user

    def invite_users(self, requester: UserModel, recipient: UserModel = None,
                     recipients: list = None, team_id=None,
                     recipient_email=None, recipient_type=None):

        assert recipient or recipients or (recipient_email and recipient_type)

        if not recipient and not recipients:
            recipient = namedtuple('Recipient', 'email user_type')(
                email=recipient_email, user_type=recipient_type)

        if not recipients and recipient:
            recipients = [recipient]

        url = reverse_lazy('rest_api:users-invite-send')
        auth = 'JWT {}'.format(requester.token)

        data = []
        for recipient in list(recipients):
            data.append({
                'recipient': recipient.email,
                'recipient_type': recipient.user_type,
            })

            if team_id:
                data[-1]['team_id'] = team_id

        if len(data) == 1:
            data = data[0]

        return self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)

    def confirm_invite(self, token, confirmer: UserModel):
        url = reverse_lazy('rest_api:users-invite-confirm')
        auth = 'JWT {}'.format(confirmer.token)
        data = {'user_invite_token': token}

        return self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)

    def revoke_invites_by_user(self, revoker: UserModel, revokee_email):
        url = reverse_lazy('rest_api:users-invite-unlink')
        auth = 'JWT {}'.format(revoker.token)
        data = {'linked_user': revokee_email}

        return self.client.delete(url, data, format='json', HTTP_AUTHORIZATION=auth)

    def revoke_from_team(self, revoker: UserModel, team_id, revokee_id):
        url = reverse_lazy('rest_api:teams-revoke', kwargs={'tid': team_id})
        auth = 'JWT {}'.format(revoker.token)
        data = {'team_id': team_id, 'user_id': revokee_id}

        return self.client.delete(url, data, format='json', HTTP_AUTHORIZATION=auth)

    def revoke_invite_by_token(
            self,
            revoker: UserModel,
            token: str = None,
            tokens: List[str] = None,
            id_=None,
            ids: List[int] = None
    ):
        assert (token or tokens or id_ or ids) and not (token and tokens and id_ and ids)

        url = reverse_lazy('rest_api:users-invite-revoke')
        auth = 'JWT {}'.format(revoker.token)

        if id_ or ids:
            data = {'id': id_} if id_ else [{'id': x} for x in list(ids)]
        else:
            data = {'user_invite_token': token} \
                if token \
                else [{'user_invite_token': t} for t in list(tokens)]

        return self.client.delete(url, data, format='json', HTTP_AUTHORIZATION=auth)

    def create_team(self, owner=None, name=None):
        url = reverse_lazy('rest_api:teams')
        owner = owner or self.coach_ca
        auth = 'JWT {}'.format(owner.token)
        data = {
            'name': name or 'the_team',
            'status': 'active',
            'tagline': 'team_tagline',
            'season': '2018',
            'location': 'Toronto',
            'owner_id': owner.id,
            'sport_id': 3,
        }
        return self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)

    def create_achievement(self, created_by, data):
        url = reverse_lazy('rest_api:achievement-list', kwargs={'uid': created_by.id})
        auth = 'JWT {}'.format(created_by.token)
        return self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)

    def get_user_pending_invites(self, user: UserModel):
        auth = 'JWT {}'.format(user.token)
        url = reverse_lazy('rest_api:user-invites', kwargs={'uid': user.id})
        return self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)

    def get_team_pending_invites(self, user: UserModel, team_id):
        auth = 'JWT {}'.format(user.token)
        url = reverse_lazy('rest_api:team-invites', kwargs={'tid': team_id})
        return self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)

    def invite_and_confirm(self, requester, recipient):
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email text'
            response = self.invite_users(requester=requester, recipient=recipient)
            token = mock_render_to_string.call_args_list[0][0][1]['token']
            self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.json())

        response = self.confirm_invite(token, recipient)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.json())

        return response

    def upload_file(self, owner, filepath: str = 'multidb_account/static/multidb_account/images/welcome-header.jpg'):
        auth = 'JWT {}'.format(owner.token)
        url = reverse_lazy('rest_api:file-list')

        with open(filepath, 'rb') as f:
            data = {'file': f}
            response = self.client.post(url, data, format='multipart', HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response
