from datetime import timedelta
from unittest import mock

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from rest_framework import status

from multidb_account.assessment.models import AssessmentTopCategory, ChosenAssessment, Assessment
from multidb_account.constants import USER_TYPE_ORG, USER_TYPE_ATHLETE
from multidb_account.team.models import Team
from rest_api.tests import ApiTests

UserModel = get_user_model()


class AssessmentTests(ApiTests):

    def test_list_athlete_assessments_permissions(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)

        self.invite_and_confirm(self.athlete_ca, self.coach_ca)

        top_categories = AssessmentTopCategory.objects.using(self.athlete_ca.country).all()

        url = reverse_lazy('rest_api:assessment-permissions', kwargs={'uid': self.athlete_ca.id})
        for top_category in top_categories:
            accessor_has_access = True
            response = self.client.get(url, {'assessor_id': self.coach_ca.id,
                                             'top_category_ids': top_category.id}, format='json',
                                       HTTP_AUTHORIZATION=auth)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data[0].get('assessor_has_access'), accessor_has_access)

    def test_update_athlete_assessments_permissions(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)

        self.invite_and_confirm(self.athlete_ca, self.coach_ca)

        top_categories = AssessmentTopCategory.objects.using(self.athlete_ca.country).all()

        url = reverse_lazy('rest_api:assessment-permissions', kwargs={'uid': self.athlete_ca.id})
        for category in top_categories:
            response = self.client.put(url, {'assessor_id': self.coach_ca.id,
                                             'assessment_top_category_id': category.id,
                                             'assessor_has_access': True}, format='json', HTTP_AUTHORIZATION=auth)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data.get('assessor_has_access'), True)

    def test_create_list_athlete_self_assessments(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)
        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.athlete_ca.id})

        # 4 stars type
        data = [{"assessment_id": 88, "value": 2}, {"assessment_id": 133, "value": 1}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('assessed_id'), self.athlete_ca.id)
            self.assertEqual(assessment.get('assessor_id'), self.athlete_ca.id)
            self.assertEqual(assessment.get('assessment_id'), data[inc].get('assessment_id'))
            self.assertEqual(int(float(assessment.get('value'))), int(float(data[inc].get('value'))))
            inc += 1

        # open value
        data = [{"assessment_id": 17, "value": float(123.545478)}, {"assessment_id": 23, "value": float(678)}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('assessed_id'), self.athlete_ca.id)
            self.assertEqual(assessment.get('assessor_id'), self.athlete_ca.id)
            self.assertEqual(assessment.get('assessment_id'), data[inc].get('assessment_id'))
            self.assertEqual(float(assessment.get('value')), data[inc].get('value'))
            inc += 1

        # 0/1 value
        data = [{"assessment_id": 34, "value": 0}, {"assessment_id": 339, "value": 1}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('assessed_id'), self.athlete_ca.id)
            self.assertEqual(assessment.get('assessor_id'), self.athlete_ca.id)
            self.assertEqual(assessment.get('assessment_id'), data[inc].get('assessment_id'))
            self.assertEqual(int(float(assessment.get('value'))), int(float(data[inc].get('value'))))
            inc += 1

    def test_create_update_athlete_self_assessments(self):
        auth = 'JWT {}'.format(self.athlete_ca.token)
        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.athlete_ca.id})

        # create
        data = [{"assessment_id": 10, "value": 3}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data[0].get('assessed_id'), self.athlete_ca.id)
        self.assertEqual(response.data[0].get('assessor_id'), self.athlete_ca.id)
        self.assertEqual(response.data[0].get('assessment_id'), data[0].get('assessment_id'))
        self.assertEqual(int(float(response.data[0].get('value'))), int(float(data[0].get('value'))))

        # update
        this_assessment_id = data[0].get('assessment_id')
        data = [{"id": response.data[0].get('id'), "value": 2}]
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0].get('assessed_id'), self.athlete_ca.id)
        self.assertEqual(response.data[0].get('assessor_id'), self.athlete_ca.id)
        self.assertEqual(response.data[0].get('assessment_id'), this_assessment_id)
        self.assertEqual(response.data[0].get('id'), data[0].get('id'))
        self.assertEqual(int(float(response.data[0].get('value'))), int(float(data[0].get('value'))))

    def test_create_update_list_coach_to_athlete_assessments(self):
        auth_coach = 'JWT {}'.format(self.coach_ca.token)
        auth_ath = 'JWT {}'.format(self.athlete_ca.token)

        self.invite_and_confirm(self.coach_ca, self.athlete_ca)

        # set permissions
        top_categories = AssessmentTopCategory.objects.using(self.athlete_ca.country).all()
        url = reverse_lazy('rest_api:assessment-permissions', kwargs={'uid': self.athlete_ca.id})
        for category in top_categories:
            response = self.client.put(url, {'assessor_id': self.coach_ca.id,
                                             'assessment_top_category_id': category.id,
                                             'assessor_has_access': True}, format='json', HTTP_AUTHORIZATION=auth_ath)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data.get('assessor_has_access'), True)

        # coach creates a team
        url = reverse_lazy('rest_api:teams')
        data = {'name': 'my_team', 'status': 'active', 'tagline': 'team_tagline', 'season': '2018',
                'location': 'Toronto', 'owner_id': self.coach_ca.id, 'sport_id': 3}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth_coach)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team_id = response.data.get('id')

        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.athlete_ca.id})
        # create: 4 stars type
        data = [{"assessment_id": 227, "value": 3, "team_id": team_id},
                {"assessment_id": 325, "value": 1, "team_id": team_id}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth_coach)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('team_id'), team_id)
            self.assertEqual(assessment.get('assessed_id'), self.athlete_ca.id)
            self.assertEqual(assessment.get('assessor_id'), self.coach_ca.id)
            self.assertEqual(assessment.get('assessment_id'), data[inc].get('assessment_id'))
            self.assertEqual(int(float(assessment.get('value'))), int(float(data[inc].get('value'))))
            inc += 1

        # update
        original_data = data
        old_response_data = response.data
        data = [{"id": old_response_data[0].get('id'), "value": 2}, {"id": old_response_data[1].get('id'), "value": 2}]
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth_coach)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('team_id'), team_id)
            self.assertEqual(assessment.get('assessed_id'), self.athlete_ca.id)
            self.assertEqual(assessment.get('assessor_id'), self.coach_ca.id)
            self.assertEqual(assessment.get('assessment_id'), original_data[inc].get('assessment_id'))
            self.assertEqual(assessment.get('id'), old_response_data[inc].get('id'))
            self.assertEqual(int(float(assessment.get('value'))), int(float(data[inc].get('value'))))
            inc += 1

        # list
        old_data = data
        get_args = {"id": old_response_data[0].get('id'), 'rendering': 'flat'}
        response = self.client.get(url, get_args, format='json', HTTP_AUTHORIZATION=auth_coach)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('team_id'), team_id)
            self.assertEqual(assessment.get('assessed_id'), self.athlete_ca.id)
            self.assertEqual(assessment.get('assessor_id'), self.coach_ca.id)
            self.assertEqual(assessment.get('assessment_id'), original_data[inc].get('assessment_id'))
            self.assertEqual(assessment.get('id'), old_response_data[inc].get('id'))
            self.assertEqual(int(float(assessment.get('value'))), int(float(old_data[inc].get('value'))))
            inc += 1

    # -----------------------------------------------------------------------

    def test_list_coach_assessments_permissions(self):
        auth = 'JWT {}'.format(self.coach_us.token)

        self.invite_and_confirm(self.coach_us, self.athlete_us)

        top_categories = AssessmentTopCategory.objects.using(self.coach_us.country).all()

        url = reverse_lazy('rest_api:assessment-permissions', kwargs={'uid': self.coach_us.id})
        for category in top_categories:
            response = self.client.get(url, {'assessor_id': self.athlete_us.id,
                                             'top_category_ids': category.id}, format='json', HTTP_AUTHORIZATION=auth)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            if category.id == 10001:
                self.assertEqual(response.data[0].get('assessor_has_access'), True)
            else:
                self.assertEqual(response.data[0].get('assessor_has_access'), False)

    def test_update_coach_assessments_permissions(self):
        auth = 'JWT {}'.format(self.coach_us.token)

        self.invite_and_confirm(self.coach_us, self.athlete_us)

        top_categories = AssessmentTopCategory.objects.using(self.coach_us.country).all()

        url = reverse_lazy('rest_api:assessment-permissions', kwargs={'uid': self.coach_us.id})
        for category in top_categories:
            response = self.client.put(url, {'assessor_id': self.athlete_us.id,
                                             'assessment_top_category_id': category.id,
                                             'assessor_has_access': True}, format='json', HTTP_AUTHORIZATION=auth)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data.get('assessor_has_access'), True)

    def test_create_list_coach_self_assessments(self):
        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.coach_us.id})

        # 4 stars type
        data = [{"assessment_id": 1, "value": 3}, {"assessment_id": 145, "value": "1"}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('assessed_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessor_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessment_id'), data[inc].get('assessment_id'))
            self.assertEqual(int(float(assessment.get('value'))), int(float(data[inc].get('value'))))
            inc += 1

        # open value
        data = [{"assessment_id": 17, "value": float(123.545478)}, {"assessment_id": 23, "value": float(678)}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('assessed_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessor_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessment_id'), data[inc].get('assessment_id'))
            self.assertEqual(float(assessment.get('value')), data[inc].get('value'))
            inc += 1

        # 0/1 value
        data = [{"assessment_id": 34, "value": 0}, {"assessment_id": 339, "value": 1}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('assessed_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessor_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessment_id'), data[inc].get('assessment_id'))
            self.assertEqual(int(float(assessment.get('value'))), int(float(data[inc].get('value'))))
            inc += 1

    def test_create_update_coach_self_assessments(self):
        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.coach_us.id})

        # create
        data = [{"assessment_id": 10, "value": 3}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data[0].get('assessed_id'), self.coach_us.id)
        self.assertEqual(response.data[0].get('assessor_id'), self.coach_us.id)
        self.assertEqual(response.data[0].get('assessment_id'), data[0].get('assessment_id'))
        self.assertEqual(int(float(response.data[0].get('value'))), int(float(data[0].get('value'))))

        # update
        this_assessment_id = data[0].get('assessment_id')
        data = [{"id": response.data[0].get('id'), "value": 2}]
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0].get('assessed_id'), self.coach_us.id)
        self.assertEqual(response.data[0].get('assessor_id'), self.coach_us.id)
        self.assertEqual(response.data[0].get('assessment_id'), this_assessment_id)
        self.assertEqual(response.data[0].get('id'), data[0].get('id'))
        self.assertEqual(int(float(response.data[0].get('value'))), int(float(data[0].get('value'))))

    def test_create_update_list_athlete_to_coach_assessments(self):
        auth_coach = 'JWT {}'.format(self.coach_us.token)
        auth_ath = 'JWT {}'.format(self.athlete_us.token)

        self.invite_and_confirm(self.athlete_us, self.coach_us)

        # set permissions
        top_categories = AssessmentTopCategory.objects.using(self.coach_us.country).all()
        url = reverse_lazy('rest_api:assessment-permissions', kwargs={'uid': self.coach_us.id})
        for category in top_categories:
            response = self.client.put(url, {'assessor_id': self.athlete_us.id,
                                             'assessment_top_category_id': category.id,
                                             'assessor_has_access': True}, format='json', HTTP_AUTHORIZATION=auth_coach)
            self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.json())
            self.assertEqual(response.data.get('assessor_has_access'), True)

        # coach creates a team
        url = reverse_lazy('rest_api:teams')
        data = {'name': 'my_team1', 'status': 'active', 'tagline': 'team_tagline', 'season': '2018',
                'location': 'Toronto', 'owner_id': self.coach_us.id, 'sport_id': 3}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth_coach)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team_id = response.data.get('id')

        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.coach_us.id})
        # create: 4 stars type
        data = [{"assessment_id": 51, "value": 3, "team_id": team_id},
                {"assessment_id": 68, "value": 1, "team_id": team_id}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth_ath)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('team_id'), team_id)
            self.assertEqual(assessment.get('assessed_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessor_id'), self.athlete_us.id)
            self.assertEqual(assessment.get('assessment_id'), data[inc].get('assessment_id'))
            self.assertEqual(int(float(assessment.get('value'))), int(float(data[inc].get('value'))))
            inc += 1

        # update
        original_data = data
        old_response_data = response.data
        data = [{"id": old_response_data[0].get('id'), "value": 2}, {"id": old_response_data[1].get('id'), "value": 2}]
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth_ath)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('team_id'), team_id)
            self.assertEqual(assessment.get('assessed_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessor_id'), self.athlete_us.id)
            self.assertEqual(assessment.get('assessment_id'), original_data[inc].get('assessment_id'))
            self.assertEqual(assessment.get('id'), old_response_data[inc].get('id'))
            self.assertEqual(int(float(assessment.get('value'))), int(float(data[inc].get('value'))))
            inc += 1

        # list
        old_data = data
        get_args = {"id": old_response_data[0].get('id'), 'rendering': 'flat'}
        response = self.client.get(url, get_args, format='json', HTTP_AUTHORIZATION=auth_ath)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inc = 0
        for assessment in response.data:
            self.assertEqual(assessment.get('team_id'), team_id)
            self.assertEqual(assessment.get('assessed_id'), self.coach_us.id)
            self.assertEqual(assessment.get('assessor_id'), self.athlete_us.id)
            self.assertEqual(assessment.get('assessment_id'), original_data[inc].get('assessment_id'))
            self.assertEqual(assessment.get('id'), old_response_data[inc].get('id'))
            self.assertEqual(int(float(assessment.get('value'))), int(float(old_data[inc].get('value'))))
            inc += 1

    def test_athlete_to_coach_assessment_timeout(self):
        auth_coach = 'JWT {}'.format(self.coach_us.token)
        auth_ath = 'JWT {}'.format(self.athlete_us.token)

        self.invite_and_confirm(self.athlete_us, self.coach_us)

        # set permissions
        top_categories = AssessmentTopCategory.objects.using(self.coach_us.country).all()
        url = reverse_lazy('rest_api:assessment-permissions', kwargs={'uid': self.coach_us.id})
        for category in top_categories:
            data = {
                'assessor_id': self.athlete_us.id,
                'assessment_top_category_id': category.id,
                'assessor_has_access': True
            }
            response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth_coach)
            self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.json())
            self.assertEqual(response.data.get('assessor_has_access'), True)

        # Access coach by athlete #1: dry_run -> OK
        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.coach_us.id})

        data = [{"assessment_id": 51, "value": 3, "dry_run": True}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth_ath)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data[0].get('id'))

        # Access coach by athlete #2 -> OK
        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.coach_us.id})

        data = [{"assessment_id": 51, "value": 3}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth_ath)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assessment = ChosenAssessment.objects.using(self.coach_us.country).get(id=response.data[0]['id'])

        # Access coach by athlete #3 -> FAIL Too soon
        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.coach_us.id})

        data = [{"assessment_id": 51, "value": 3}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth_ath)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Access coach by athlete #4: dry_run -> FAIL Too soon
        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.coach_us.id})

        data = [{"assessment_id": 51, "value": 3, "dry_run": True}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth_ath)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Tweak last assessment's date
        assessment.date_assessed = timezone.now() - timedelta(weeks=6)
        assessment.save(update_fields=['date_assessed'])

        # Access coach by athlete #5 -> OK
        url = reverse_lazy('rest_api:chosen-assessments', kwargs={'uid': self.coach_us.id})

        data = [{"assessment_id": 51, "value": 4}]
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth_ath)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data[0].get('id'))


class PrivateAssessmentTests(ApiTests):
    def test_team_private_assessments(self):
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

        # Make team private
        team.is_private = True
        team.save()

        # Make private assesssment
        private_assesssment = self._make_private_assessment(team, localized_db)

        # GET assessment list including private ones by coach-owner
        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:assessments')
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        got_assessments = self._get_assessment_objs_from_tree(response.data)
        got_private_assessment_ids = {x['id'] for x in got_assessments if x['is_private']}
        self.assertEqual(got_private_assessment_ids, {private_assesssment.id})

        # GET assessment list including privates one by athlete-member
        auth = 'JWT {}'.format(self.athlete_us.token)
        url = reverse_lazy('rest_api:assessments')
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        got_assessments = self._get_assessment_objs_from_tree(response.data)
        got_private_assessment_ids = {x['id'] for x in got_assessments if x['is_private']}
        self.assertEqual(got_private_assessment_ids, {private_assesssment.id})

        # GET assessment list including privates one by alien-user
        alien_athlete = self.create_random_user(country=localized_db, user_type=USER_TYPE_ATHLETE)
        auth = 'JWT {}'.format(alien_athlete.token)
        url = reverse_lazy('rest_api:assessments')
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        got_assessments = self._get_assessment_objs_from_tree(response.data)
        got_private_assessment_ids = {x['id'] for x in got_assessments if x['is_private']}
        self.assertEqual(got_private_assessment_ids, set())

    def test_organisation_private_assessments(self):
        localized_db = self.coach_us.country

        # Create an organisation
        org = self._create_org(own_assessments_only=False)

        # Create an org-member
        org.members.add(self.coach_us)

        # Make private assesssment
        private_assesssment = self._make_private_assessment(org, localized_db)

        # GET assessment list including private ones by coach-owner
        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:assessments')
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        got_assessments = self._get_assessment_objs_from_tree(response.data)
        got_private_assessment_ids = {x['id'] for x in got_assessments if x['is_private']}
        self.assertEqual(got_private_assessment_ids, {private_assesssment.id})

        # GET assessment list excluding private ones by alien-user
        auth = 'JWT {}'.format(self.athlete_us.token)
        url = reverse_lazy('rest_api:assessments')
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        got_assessments = self._get_assessment_objs_from_tree(response.data)
        got_private_assessment_ids = {x['id'] for x in got_assessments if x['is_private']}
        self.assertEqual(got_private_assessment_ids, set())

        # Make org `own_assessments_only`
        org.own_assessments_only = True
        org.save()

        # GET own_assessments_only assessment list by coach-owner
        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:assessments')

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        got_assessments = self._get_assessment_objs_from_tree(response.data)
        got_private_assessment_ids = {x['id'] for x in got_assessments if x['is_private']}
        self.assertEqual(got_private_assessment_ids, {private_assesssment.id})

    def test_org_own_assessments_on(self):
        """
        For users that are members of an organization with `own_assessments_only=True` we want to return only
        assessments that are in many to many relations with the organization (private + public)
        """
        # Create an organisation
        org = self._create_org(own_assessments_only=True, members=[self.coach_us])

        # Make org assesssments: private and non-private
        private_assesssment = self._make_private_assessment(org)
        public_org_assesssment = self._make_org_private_public_assessment(org)
        public_everywhere_assessments = {x for x in
                                         Assessment.objects.using(self.coach_us.country)
                                         .filter(is_public_everywhere=True).values_list('id', flat=True)}

        # GET assessment list by coach - org's member
        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:assessments')
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        got_assessments = self._get_assessment_objs_from_tree(response.data)

        # Expect only own_assessments from the `Organisation.own_assessments` m2m
        got_assessment_ids = {x['id'] for x in got_assessments}
        expect_assessment_ids = {private_assesssment.id, public_org_assesssment.id} | public_everywhere_assessments
        self.assertEqual(got_assessment_ids, expect_assessment_ids)

    def test_org_own_assessments_off(self):
        """
        For users that are members of an organization with `own_assessments_only=False` we want to return:
        1. all our public assessments (`is_private=False` or `is_public_everywhere=True`)
        +
        2. all private assessments that are added to the org's own_assessments m2m.
        """
        # Create an organisation
        org = self._create_org(own_assessments_only=False, members=[self.coach_us])

        # Make org assesssments: private and non-private
        private_assesssment = self._make_private_assessment(org)
        public_org_assesssment = self._make_org_private_public_assessment(org)
        public_everywhere_assessments = {x for x in
                                         Assessment.objects.using(self.coach_us.country)
                                         .filter(is_public_everywhere=True).values_list('id', flat=True)}

        # GET assessment list by coach - org's member
        auth = 'JWT {}'.format(self.coach_us.token)
        url = reverse_lazy('rest_api:assessments')
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        got_assessments = self._get_assessment_objs_from_tree(response.data)

        # Expect own_assessments from the `Organisation.own_assessments` m2m
        got_assessment_ids = {x['id'] for x in got_assessments}
        self.assertIn(private_assesssment.id, got_assessment_ids)
        self.assertIn(public_org_assesssment.id, got_assessment_ids)

        # Expect we get not only org m2m own_assessments
        org_assessment_ids = {private_assesssment.id, public_org_assesssment.id}
        self.assertGreater(len(got_assessment_ids), len(org_assessment_ids))

        # Expect all other public assessments (got_public_assessment_ids is a subset of got_assessment_ids)
        got_public_assessment_ids = {x['id'] for x in got_assessments if not x['is_private']}
        self.assertLess(got_public_assessment_ids, got_assessment_ids)

    @staticmethod
    def _make_private_assessment(owner, localized_db='us'):
        """ `owner` can be either `Team` obj or `Organisation` """
        private_assesssment = Assessment.objects.using(localized_db).first()
        private_assesssment.is_private = True
        private_assesssment.save()
        field = 'assessments' if isinstance(owner, Team) else 'own_assessments'
        getattr(owner, field).add(private_assesssment)
        return private_assesssment

    @staticmethod
    def _make_org_private_public_assessment(org, localized_db='us'):
        """ Add an assessment to the Organisation whithout making it `is_private = True` """
        public_assesssment = Assessment.objects.using(localized_db).filter(is_private=False).first()
        org.own_assessments.add(public_assesssment)
        return public_assesssment

    def _create_org(self, own_assessments_only, localized_db='us', members=None):
        url = reverse_lazy('rest_api:users')
        data = {}
        org_details = {
            'email': 'organisation@test.com',
            'country': localized_db,
            'user_type': USER_TYPE_ORG,
            'password': 'password',
            'confirm_password': 'password',
            'organisation_name': 'TheOrg',
        }
        data.update(self.user_common_data)
        data.update(org_details)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = UserModel.objects.using(localized_db).get(pk=response.data['id'])
        org = user.organisation

        if members:
            org.members.add(*members)

        if own_assessments_only:
            org.own_assessments_only = True
            org.save()

        return org

    def _get_assessment_objs_from_tree(self, data):
        assessments = []
        for item in data:
            if 'childs' in item:
                assessments.extend(self._get_assessment_objs_from_tree(item['childs']))
            else:
                assessments.append(item)
        return assessments
