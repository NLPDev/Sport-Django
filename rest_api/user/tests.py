from django.contrib.auth import get_user_model
from django.core import signing
from django.core.urlresolvers import reverse_lazy
from django.forms.models import model_to_dict
from rest_framework import status

from multidb_account.constants import USER_TYPE_ATHLETE, USER_TYPE_COACH, PROFILE_PICTURE_WIDTH, PROFILE_PICTURE_HEIGHT, \
    USER_TYPE_ORG
from multidb_account.user.models import CoachUser, AthleteUser
from rest_api.tests import ApiTests

UserModel = get_user_model()


class UserTests(ApiTests):

    # ------------------------------------------------------------------------------

    def test_create_athlete_user(self):
        """
        Ensure we can create a new athlete user.
        """
        url = reverse_lazy("rest_api:users")
        data = {}

        # Missing required fields: passwords + last_name
        athlete_details = {
            'email': 'athlete-create@test.com',
            'country': 'ca',
            'user_type': USER_TYPE_ATHLETE,
        }
        data.update(self.user_common_data)
        data.update(self.athlete_extended_data)
        data.update(athlete_details)
        data.pop('last_name')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # OK
        athlete_details = {'email': 'athlete-create@test.com',
                           'country': 'ca',
                           'user_type': USER_TYPE_ATHLETE,
                           'password': 'password',
                           'confirm_password': 'password'}
        data.update(self.user_common_data)
        data.update(self.athlete_extended_data)
        data.update(athlete_details)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for item in self.athlete_extended_profile_items:
            self.assertEqual(response.data.get(item), data.get(item))
        self.assertEqual(response.data.get('payment_status'), 'no_card')
        self.assertEqual(response.data.get('team_memberships'), [])
        self.assertEqual(response.data.get('linked_users'), [])

    def test_change_password_athlete(self):
        url = reverse_lazy("rest_api:password-change")
        auth = 'JWT {}'.format(self.athlete_ca.token)
        data = {"current_password": "password",
                "confirm_password": "password2",
                "password": "password2"}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        login = reverse_lazy("rest_api:login")
        data = {"email": self.athlete_ca.email, "password": "password2"}
        response = self.client.post(login, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_athlete(self):
        url = reverse_lazy("rest_api:logout")
        auth = 'JWT {}'.format(self.athlete_ca.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_athlete(self):
        url = reverse_lazy("rest_api:login")
        data = {"email": self.athlete_ca.email, "password": "password"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def cancel_athlete(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)
        data = {"token": 'tok_visa', 'plan': 'monthly'}
        # Set payment card + plan
        url = reverse_lazy('rest_api:payment', kwargs={'uid': self.athlete_ca.id})
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('token'), data.get('token'))
        self.assertEqual(response.data.get('plan'), data.get('plan'))

        # Simulate the invite step
        invite_token = signing.dumps({'requester_email': self.athlete_ca.email,
                                      'requester_type': self.athlete_ca.user_type,
                                      'localized_db': self.athlete_ca.country,
                                      'recipient_email': self.coach_ca.email,
                                      'recipient_type': self.coach_ca.user_type
                                      }, salt='user_connection')

        # Invite confirm step
        url = reverse_lazy('rest_api:users-invite-confirm')
        data = {'user_invite_token': invite_token}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('requester_type'), self.athlete_ca.user_type)
        self.assertEqual(response.data.get('requester_first_name'), self.athlete_ca.first_name)
        self.assertEqual(response.data.get('requester_last_name'), self.athlete_ca.last_name)
        self.assertEqual(response.data.get('requester_id'), self.athlete_ca.id)

        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.athlete_ca.id})
        response = self.client.delete(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('email'), self.athlete_ca.email)

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        athlete_canceled = AthleteUser.objects.using(self.athlete_ca.country).get(user_id=self.athlete_ca.id)
        self.assertEqual(athlete_canceled.user.is_active, False)
        self.assertEqual(athlete_canceled.customer.payment_status, 'no_card')
        self.assertEqual(athlete_canceled.coaching_set.all().count(), 0)
        assessed = athlete_canceled.get_assessed()
        assessor = athlete_canceled.get_assessor()
        self.assertEqual(assessed.assessmenttopcategorypermission_set.all().count(), 0)
        self.assertEqual(assessor.assessmenttopcategorypermission_set.all().count(), 0)

    def test_list_athlete_details(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.athlete_ca.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in self.profile_items:
            self.assertEqual(response.data.get(item), model_to_dict(self.athlete_ca).get(item))
        # Athlete extended profile
        self.assertEqual(response.data.get('referral_code'), self.athlete_ca.athleteuser.referral_code)
        self.assertFalse(response.data['new_dashboard'])
        self.assertEqual(response.data.get('athlete_terms_conditions'),
                         self.athlete_ca.athleteuser.athlete_terms_conditions)
        self.assertEqual(response.data.get('payment_status'), 'no_card')

    def test_update_athlete_details(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)
        data = {"email": "athlete-updated@ca.ca",
                "province_or_state": "Alberta",
                "city": "Calgary",
                "first_name": "athlete-updated-lname",
                "last_name": "athlete-updated-fname",
                "date_of_birth": "1989-12-23",
                "newsletter": False,
                "terms_conditions": True,
                "measuring_system": "imperial",
                "tagline": "My updated tagline",
                'referral_code': 'RC2',
                'schools': tuple(),
                'athlete_terms_conditions': True}
        # "profile_picture": File(open('logo.png')),v
        # chosen_sport
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.athlete_ca.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in data.items():
            self.assertEqual(response.data.get(item), data.get(item))
        self.assertEqual(response.data.get('payment_status'), 'no_card')

    def test_upload_profile_picture_and_resize(self):
        user = self.athlete_ca
        auth = 'JWT {}'.format(user.token)
        url = reverse_lazy('rest_api:user-picture', kwargs={'uid': self.athlete_ca.id})

        # Upload an image
        with open('multidb_account/static/multidb_account/images/welcome-header.jpg', 'rb') as f:
            data = {'profile_picture': f}
            response = self.client.put(url, data, format='multipart', HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert result size and filename
        user.refresh_from_db()
        self.assertLessEqual(user.profile_picture.height, PROFILE_PICTURE_HEIGHT)
        self.assertLessEqual(user.profile_picture.width, PROFILE_PICTURE_WIDTH)

    def test_set_athlete_payment_card(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)
        data = {"token": 'tok_visa'}
        # Set payment card
        url = reverse_lazy('rest_api:payment-card', kwargs={'uid': self.athlete_ca.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('token'), data.get('token'))

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('brand'), 'Visa')

    def test_update_athlete_payment_card(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)
        data = {"token": 'tok_visa'}
        # Set payment card
        url = reverse_lazy('rest_api:payment-card', kwargs={'uid': self.athlete_ca.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('token'), data.get('token'))

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('brand'), 'Visa')

        # Update payment card
        data = {"token": 'tok_mastercard'}
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('token'), data.get('token'))

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('brand'), 'MasterCard')

    def test_set_athlete_payment_plan(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)

        # Set payment card first
        data = {"token": 'tok_visa'}
        url = reverse_lazy('rest_api:payment-card', kwargs={'uid': self.athlete_ca.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('token'), data.get('token'))

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('brand'), 'Visa')

        data = {"plan": 'monthly'}
        # Set payment plan
        url = reverse_lazy('rest_api:payment-plan', kwargs={'uid': self.athlete_ca.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('plan'), data.get('plan'))

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('plan'), data.get('plan'))

    def test_update_athlete_payment_plan(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)

        # Set payment card first
        data = {"token": 'tok_visa'}
        url = reverse_lazy('rest_api:payment-card', kwargs={'uid': self.athlete_ca.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('token'), data.get('token'))

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('brand'), 'Visa')

        # Set payment plan
        data = {'plan': 'monthly'}
        url = reverse_lazy('rest_api:payment-plan', kwargs={'uid': self.athlete_ca.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('plan'), data.get('plan'))

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('plan'), data.get('plan'))

        # Update payment plan
        data = {'plan': 'yearly'}
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('plan'), data.get('plan'))

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('plan'), data.get('plan'))

    def test_set_athlete_payment_plan_card(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)
        data = {"token": 'tok_visa', 'plan': 'monthly'}
        # Set payment card + plan
        url = reverse_lazy('rest_api:payment', kwargs={'uid': self.athlete_ca.id})
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('token'), data.get('token'))
        self.assertEqual(response.data.get('plan'), data.get('plan'))

        url = reverse_lazy('rest_api:payment-card', kwargs={'uid': self.athlete_ca.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('brand'), 'Visa')

        url = reverse_lazy('rest_api:payment-plan', kwargs={'uid': self.athlete_ca.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('plan'), data.get('plan'))

    def test_athlete_coach_connection(self):

        # Simulate the invite step
        response = self.invite_and_confirm(self.athlete_ca, self.coach_ca)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('requester_type'), self.athlete_ca.user_type)
        self.assertEqual(response.data.get('requester_first_name'), self.athlete_ca.first_name)
        self.assertEqual(response.data.get('requester_last_name'), self.athlete_ca.last_name)
        self.assertEqual(response.data.get('requester_id'), self.athlete_ca.id)

    # -----------------------------------------------------------------------

    def test_create_coach_user(self):
        """
        Ensure we can create a new coach user.
        """
        url = reverse_lazy("rest_api:users")
        data = self.user_common_data
        data.update({'email': 'coach-create@test.com', 'country': 'us', 'user_type': USER_TYPE_COACH,
                     'password': 'password', 'confirm_password': 'password'})
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for item in self.profile_items:
            self.assertEqual(response.data.get(item), data.get(item))
        self.assertEqual(response.data.get('linked_users'), [])
        self.assertEqual(response.data.get('team_memberships'), [])
        self.assertEqual(response.data.get('team_ownerships'), [])

    def test_change_password_coach(self):
        url = reverse_lazy("rest_api:password-change")
        auth = 'JWT {}'.format(self.coach_us.token)
        data = {"current_password": "password",
                "confirm_password": "password2",
                "password": "password2"}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        login = reverse_lazy("rest_api:login")
        data = {"email": self.coach_us.email, "password": "password2"}
        response = self.client.post(login, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_coach(self):
        url = reverse_lazy("rest_api:logout")
        auth = 'JWT {}'.format(self.coach_us.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_coach(self):
        url = reverse_lazy("rest_api:login")
        data = {"email": self.coach_us.email, "password": "password"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def cancel_coach(self):
        auth = 'JWT {}'.format(self.coach_us.token)

        # Simulate the invite step
        invite_token = signing.dumps({'requester_email': self.coach_us.email,
                                      'requester_type': self.coach_us.user_type,
                                      'localized_db': self.coach_us.country,
                                      'recipient_email': self.athlete_us.email,
                                      'recipient_type': self.athlete_us.user_type
                                      }, salt='user_connection')

        # Invite confirm step
        url = reverse_lazy('rest_api:users-invite-confirm')
        data = {'user_invite_token': invite_token}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('requester_type'), self.coach_us.user_type)
        self.assertEqual(response.data.get('requester_first_name'), self.coach_us.first_name)
        self.assertEqual(response.data.get('requester_last_name'), self.coach_us.last_name)

        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.coach_us.id})
        response = self.client.delete(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('email'), self.coach_us.email)

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        coach_canceled = CoachUser.objects.using(self.coach_us.country).get(user_id=self.coach_us.id)
        self.assertEqual(coach_canceled.user.is_active, False)
        self.assertEqual(coach_canceled.coaching_set.all().count(), 0)
        assessed = coach_canceled.get_assessed()
        assessor = coach_canceled.get_assessor()
        self.assertEqual(assessed.assessmenttopcategorypermission_set.all().count(), 0)
        self.assertEqual(assessor.assessmenttopcategorypermission_set.all().count(), 0)

    def test_list_coach_details(self):
        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.coach_us.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in self.profile_items:
            self.assertEqual(response.data.get(item), model_to_dict(self.coach_us).get(item))

    def test_update_coach_details(self):
        auth = 'JWT {}'.format(self.coach_us.token)
        data = {"email": "coach-updated@ca.ca",
                "province_or_state": "Alberta",
                "city": "Calgary",
                "first_name": "coach-updated-lname",
                "last_name": "coach-updated-fname",
                "date_of_birth": "1989-12-23",
                "newsletter": False,
                "terms_conditions": True,
                "measuring_system": "imperial",
                "schools": tuple(),
                "tagline": "My updated tagline"}
        # "profile_picture": File(open('logo.png')),
        # chosen_sport
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.coach_us.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in data.items():
            self.assertEqual(response.data.get(item), data.get(item))

    def test_update_athlete_promocode(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)
        uid = self.athlete_ca.id

        data = {"promocode": "free"}
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': uid})
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('promocode'), data.get('promocode'))

        data = {"promocode": ""}
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': uid})
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('promocode'), data.get('promocode'))

    def test_coach_athlete_connection(self):

        response = self.invite_and_confirm(self.coach_us, self.athlete_us)

        self.assertEqual(response.data.get('requester_type'), self.coach_us.user_type)
        self.assertEqual(response.data.get('requester_first_name'), self.coach_us.first_name)
        self.assertEqual(response.data.get('requester_last_name'), self.coach_us.last_name)


class OrganisationTests(ApiTests):

    def test_create_minimal_org_user(self):
        """
        Ensure we can create a new organisation user.
        """
        url = reverse_lazy("rest_api:users")
        data = {}
        org_details = {
            'email': 'organisation@test.com',
            'country': 'ca',
            'user_type': USER_TYPE_ORG,
            'organisation_name': 'TheOrg',
        }
        org_common_data = self.user_common_data.copy()
        org_common_data.pop('last_name')
        data.update(org_common_data)
        data.update(org_details)
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for item in self.athlete_extended_profile_items:
            if item == 'last_name':
                self.assertEqual(response.data.get(item), data.get(item, ''))
            else:
                self.assertEqual(response.data.get(item), data.get(item))
        self.assertIsNone(response.data.get('payment_status'))
        self.assertEqual(response.data.get('team_memberships'), [])
        self.assertEqual(response.data.get('team_ownerships'), [])
        self.assertEqual(response.data.get('linked_users'), [])

        user = UserModel.objects.using(org_details['country']).get(pk=response.data['id'])
        self.assertEqual(user.user_type, USER_TYPE_ORG)
        self.assertEqual(user.is_active, False)

        org = user.organisation
        self.assertEqual(org.size, org_details.get('size'))
        self.assertEqual(org.description, org_details.get('description', ''))
        self.assertEqual(org.sports, org_details.get('sports', []))
        self.assertEqual(org.name, org_details.get('organisation_name', []))

    def test_create_org_user_with_max_data(self):
        """
        Ensure we can create a new organisation user.
        """
        url = reverse_lazy("rest_api:users")
        data = {}
        org_details = {
            'email': 'organisation@test.com',
            'country': 'ca',
            'user_type': USER_TYPE_ORG,
            'password': 'password',
            'confirm_password': 'password',
            'size': 1,
            'description': 'TheDescription',
            'sports': ['sport1', 'sport2'],
            'organisation_name': 'TheOrg',
        }
        data.update(self.user_common_data)
        data.update(org_details)
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for item in self.athlete_extended_profile_items:
            self.assertEqual(response.data.get(item), data.get(item))
        self.assertIsNone(response.data.get('payment_status'))
        self.assertEqual(response.data.get('team_memberships'), [])
        self.assertEqual(response.data.get('linked_users'), [])

        user = UserModel.objects.using(org_details['country']).get(pk=response.data['id'])
        self.assertEqual(user.user_type, USER_TYPE_ORG)
        self.assertEqual(user.is_active, False)

        org = user.organisation
        self.assertEqual(org.size, org_details['size'])
        self.assertEqual(org.description, org_details['description'])
        self.assertEqual(org.sports, org_details['sports'])
        self.assertEqual(org.name, org_details['organisation_name'])

    def test_change_password_org(self):
        url = reverse_lazy("rest_api:password-change")
        auth = 'JWT {}'.format(self.org_ca.token)
        data = {"current_password": "password",
                "confirm_password": "password2",
                "password": "password2"}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        login = reverse_lazy("rest_api:login")
        data = {"email": self.org_ca.email, "password": "password2"}
        response = self.client.post(login, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_org(self):
        url = reverse_lazy("rest_api:logout")
        auth = 'JWT {}'.format(self.org_ca.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_org(self):
        url = reverse_lazy("rest_api:login")
        data = {"email": self.org_ca.email, "password": "password"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_org_details(self):
        auth = 'JWT {}'.format(self.org_ca.token)
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.org_ca.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in self.profile_items:
            self.assertEqual(response.data.get(item), model_to_dict(self.org_ca).get(item))
        # Extended profile
        self.assertEqual(response.data.get('terms_conditions'), self.org_ca.terms_conditions)
        self.assertFalse(response.data['new_dashboard'])

    def test_update_org_details(self):
        auth = 'JWT {}'.format(self.org_ca.token)
        data = {"email": "org-updated@ca.ca",
                "province_or_state": "Alberta",
                "city": "Calgary",
                "first_name": "org-updated-lname",
                "last_name": "org-updated-fname",
                "date_of_birth": "1989-12-23",
                "newsletter": False,
                "terms_conditions": True,
                "measuring_system": "imperial",
                "tagline": "My updated tagline",
                'schools': tuple(),
                'organisation_name': 'TheOrg',
                'referral_code': 'RC2'}
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.org_ca.id})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in data.items():
            self.assertEqual(response.data.get(item), data.get(item))

    def test_upload_profile_picture_and_resize(self):
        user = self.org_ca
        auth = 'JWT {}'.format(user.token)
        url = reverse_lazy('rest_api:user-picture', kwargs={'uid': self.org_ca.id})

        # Upload an image
        with open('multidb_account/static/multidb_account/images/welcome-header.jpg', 'rb') as f:
            data = {'profile_picture': f}
            response = self.client.put(url, data, format='multipart', HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert result size and filename
        user.refresh_from_db()
        self.assertLessEqual(user.profile_picture.height, PROFILE_PICTURE_HEIGHT)
        self.assertLessEqual(user.profile_picture.width, PROFILE_PICTURE_WIDTH)

    def test_login_by_multiple_users(self):
        # Add second user to the org's login_users
        self.org_ca_1 = self.create_random_user(country='ca', user_type=USER_TYPE_ORG, organisation_name='TheOrg1')
        self.org_ca_2 = self.create_random_user(country='ca', user_type=USER_TYPE_ORG, organisation_name='TheOrg2')
        org1 = self.org_ca_1.organisation
        org1.login_users.add(self.org_ca_2)

        # Login: OK
        url = reverse_lazy("rest_api:login")
        data = {"email": self.org_ca_2.email, "password": "password"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check org's details by user 1
        auth = 'JWT {}'.format(self.org_ca_1.token)
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.org_ca_1.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.data['organisation_name'], 'TheOrg1')

        # Check org's details by user 2
        auth = 'JWT {}'.format(self.org_ca_2.token)
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.org_ca_2.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.data['organisation_name'], 'TheOrg1')
