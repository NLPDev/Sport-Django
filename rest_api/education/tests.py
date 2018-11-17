from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from rest_framework import status
from multidb_account.education.models import Education

from rest_api.tests import ApiTests

UserModel = get_user_model()


class EducationTests(ApiTests):

    def test_education_crud(self):
        user = self.coach_ca
        user2 = self.athlete_ca
        auth = 'JWT {}'.format(user.token)
        auth2 = 'JWT {}'.format(user2.token)
        url = reverse_lazy('rest_api:user-educations', kwargs={'uid': user.id})

        # Create an education by user1
        data = {
            'gpa': 2.1,
            'school': 'TheSchool',
            'current': True,
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        education = Education.objects.using(user.country).get(pk=response.data['id'])
        self.assertEqual(education.user, user)
        self.assertEqual(str(education.gpa), str(data['gpa']))
        self.assertEqual(education.school, data['school'])
        self.assertEqual(education.current, data['current'])

        # Create an education by user2
        data = {
            'gpa': 3.1,
            'school': 'TheSchool#2',
            'current': False,
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth2)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        education2 = Education.objects.using(user2.country).get(pk=response.data['id'])
        self.assertEqual(education2.user, user2)

        # GET all educations of user1
        url = reverse_lazy('rest_api:user-educations', kwargs={'uid': user.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # GET education of user2 by user1: OK
        url2 = reverse_lazy('rest_api:user-educations', kwargs={'uid': user2.id, 'eid': education2.pk})
        response = self.client.get(url2, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET education of user1
        url = reverse_lazy('rest_api:user-educations', kwargs={'uid': user.id, 'eid': education.pk})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(education.user.id, response.data['user'])
        self.assertEqual(str(education.gpa), str(response.data['gpa']))
        self.assertEqual(education.school, response.data['school'])
        self.assertEqual(education.current, response.data['current'])

        # PUT
        old_gpa = education.gpa
        old_current = education.current
        gpa = 4.1
        data = {'gpa': gpa, 'current': False}
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        education.refresh_from_db()
        self.assertEqual(str(education.gpa), str(gpa))
        self.assertNotEqual(str(education.gpa), str(old_gpa))
        self.assertNotEqual(education.current, old_current)

        # PATCH
        old_gpa = education.gpa
        old_current = education.current
        gpa = 5.1
        data = {'gpa': gpa, 'current': True}
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        education.refresh_from_db()
        self.assertEqual(str(education.gpa), str(gpa))
        self.assertNotEqual(str(education.gpa), str(old_gpa))
        self.assertNotEqual(education.current, old_current)

        # PUT incorrect education (of another owner)
        url2 = reverse_lazy('rest_api:user-educations', kwargs={'uid': user.id, 'eid': education2.pk})

        gpa = 6.1
        data = {'gpa': gpa}
        response = self.client.put(url2, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # PATCH incorrect education (of another owner)
        response = self.client.patch(url2, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE incorrect education (of another owner)
        response = self.client.delete(url2, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE correct education (ours)
        response = self.client.delete(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_multiple_educations(self):
        user = self.coach_ca
        auth = 'JWT {}'.format(user.token)
        url = reverse_lazy('rest_api:user-educations', kwargs={'uid': user.id})

        # Create an education by user1
        data = {
            'gpa': 1.0,
            'school': 'TheSchool',
            'current': True,
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        education = Education.objects.using(user.country).get(pk=response.data['id'])
        self.assertEqual(education.user, user)
        self.assertEqual(str(education.gpa), str(data['gpa']))
        self.assertEqual(education.school, data['school'])
        self.assertEqual(education.current, data['current'])

        # Create an education2 by user1
        data = {
            'gpa': 2.0,
            'school': 'TheSchool2',
            'current': False,
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        education2 = Education.objects.using(user.country).get(pk=response.data['id'])
        self.assertEqual(education2.user, user)
        self.assertEqual(str(education2.gpa), str(data['gpa']))
        self.assertEqual(education2.school, data['school'])
        self.assertEqual(education2.current, data['current'])

        # GET all educations of user1
        url = reverse_lazy('rest_api:user-educations', kwargs={'uid': user.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # GET current user's detail
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': user.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
