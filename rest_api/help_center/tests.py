from datetime import datetime
from unittest import mock

from django.core.urlresolvers import reverse_lazy
from rest_framework import status

from multidb_account.help_center.models import HelpCenterReport, OrganisationSupport
from rest_api.tests import ApiTests


class HelpCenterTests(ApiTests):
    def test_help_center(self):
        user = self.coach_ca
        auth = 'JWT {}'.format(user.token)
        url = reverse_lazy('rest_api:help-center-report-list')
        help_center_emails = ['test1@email.com', 'test2@email.com']

        min_data = {
            'organization': 'TheOrg',
            'coach_name': 'TheCoach',
            'details': 'TheCoach',
            'date': '2017-01-01',
        }

        max_data = dict(min_data, **{'name': 'TheName'})

        # Check POST with missing fields
        for no_field in min_data.keys():
            bad_data = {k: v for k, v in min_data.items() if k != no_field}
            response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=auth)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Check POST with minimal required data
        response = self.client.post(url, min_data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check POST with all the data
        with self.settings(HELP_CENTER_FORM_EMAILS=help_center_emails):
            with mock.patch('multidb_account.help_center.models.send_mail') as mocked:
                response = self.client.post(url, max_data, format='json', HTTP_AUTHORIZATION=auth)
                self.assertEqual(mocked.call_count, 1)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check DB
        self.assertEqual(HelpCenterReport.objects.using(user.country).count(), 2)

        got_max_data = HelpCenterReport.objects.using(user.country).latest('id')
        for field in max_data.keys():
            exp_value = max_data[field] if field != 'date' else datetime.strptime(max_data[field], "%Y-%m-%d").date()
            self.assertEqual(getattr(got_max_data, field), exp_value)


class OrganisationSupportTests(ApiTests):
    def test_organisation_support(self):
        user = self.org_ca
        auth = 'JWT {}'.format(user.token)
        url = reverse_lazy('rest_api:organisation-support-list')
        support_emails = ['test1@email.com', 'test2@email.com']

        min_data = {
            'email': 'from@email.com',
            'details': 'TheDetails',
            'name': 'TheName',
            'support_type': 'TheType',
        }
        max_data = dict(min_data, **{'phone_number': '+71234567890'})

        # Check POST with missing fields
        for no_field in min_data.keys():
            bad_data = {k: v for k, v in min_data.items() if k != no_field}
            response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=auth)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Check POST with minimal required data
        response = self.client.post(url, min_data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check POST with all the data
        with self.settings(HELP_CENTER_ORG_SUPPORT_FORM_EMAILS=support_emails):
            with mock.patch('multidb_account.help_center.models.send_mail') as mocked:
                response = self.client.post(url, max_data, format='json', HTTP_AUTHORIZATION=auth)
                self.assertEqual(mocked.call_count, 1)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check DB
        self.assertEqual(OrganisationSupport.objects.using(user.country).count(), 2)

        got_max_data = OrganisationSupport.objects.using(user.country).latest('id')
        for field in max_data.keys():
            exp_value = max_data[field]
            self.assertEqual(getattr(got_max_data, field), exp_value)
