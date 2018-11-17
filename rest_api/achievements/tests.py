from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from rest_framework import status
from rest_api.tests import ApiTests

from multidb_account.constants import USER_TYPE_COACH
from multidb_account.achievements.models import Achievement, Badge

UserModel = get_user_model()


class AchievementTests(ApiTests):

    def test_badges_list(self):
        auth = 'JWT {}'.format(self.coach_ca.token)
        url = reverse_lazy('rest_api:badge-list')
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(len(response.data), Badge.objects.using(self.coach_ca.country).count())

    def test_achievements(self):
        localized_db = self.coach_ca.country

        # Create some badges
        badge = Badge.objects.using(localized_db).create(image_url='http://some/url', name='TheBadge')
        badge2 = Badge.objects.using(localized_db).create(image_url='http://some/url2')

        coach_ca2 = self.create_random_user(country=self.coach_ca.country, user_type=USER_TYPE_COACH)

        # POST incorrect data: empty
        response = self.create_achievement(self.coach_ca, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Make some data
        class MyDict(dict):
            def without(self, key):
                new_d = self.copy()
                new_d.pop(key, None)
                return new_d

        data_min = MyDict({
            'title': 'TheTitle',
            'date': timezone.now().date().isoformat(),
            'badge_id': badge.id,
        })

        data_max = MyDict(data_min, **{
            'competition': 'TheCompetition',
            'team': 'Some team name',
        })

        # POST incorrect data: no title
        response = self.create_achievement(self.coach_ca, data_min.without('title'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST incorrect data: no datetime
        response = self.create_achievement(self.coach_ca, data_min.without('date'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST incorrect data: no badge_id
        response = self.create_achievement(self.coach_ca, data_min.without('badge_id'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST correct data
        response = self.create_achievement(self.coach_ca, data_max)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        achievement = Achievement.objects.using(localized_db).get(id=response.data['id'])
        self.assertEqual(achievement.title, data_max['title'])
        self.assertEqual(achievement.date.isoformat(), data_max['date'])
        self.assertEqual(achievement.badge_id, data_max['badge_id'])
        self.assertEqual(achievement.competition, data_max['competition'])
        self.assertEqual(achievement.team, data_max['team'])

        # POST correct data #2
        data = dict(data_max, **{'badge_id': badge2.id})
        data.pop('competition')
        data.pop('team')

        response = self.create_achievement(coach_ca2, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        achievement2 = Achievement.objects.using(localized_db).get(id=response.data['id'])
        self.assertEqual(achievement2.title, data['title'])
        self.assertEqual(achievement2.date.isoformat(), data['date'])
        self.assertEqual(achievement2.badge_id, data['badge_id'])
        self.assertIsNone(data.get('competition'))
        self.assertIsNone(data.get('team'))

        # GET
        url = reverse_lazy('rest_api:achievement-detail', kwargs={'uid': self.coach_ca.id, 'aid': achievement.pk})
        auth = 'JWT {}'.format(self.coach_ca.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(achievement.title, data_max['title'])
        self.assertEqual(achievement.date.isoformat(), data_max['date'])
        self.assertEqual(achievement.badge_id, data_max['badge_id'])
        self.assertEqual(achievement.competition, data_max['competition'])
        self.assertEqual(achievement.team, data_max['team'])

        # PUT
        auth = 'JWT {}'.format(self.coach_ca.token)
        old_title = achievement.title
        title = 'new title'
        data = dict(data_min, **{'title': title})
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        achievement.refresh_from_db()
        self.assertEqual(achievement.title, title)
        self.assertNotEqual(achievement.title, old_title)

        # PATCH
        old_title = achievement.title
        title = 'new new title'
        data = {'title': title}
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        achievement.refresh_from_db()
        self.assertEqual(achievement.title, title)
        self.assertNotEqual(achievement.title, old_title)

        # PUT incorrect created_by
        data = {'created_by': coach_ca2.id}
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # PATCH our achievement by other user
        auth2 = 'JWT {}'.format(coach_ca2.token)
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=auth2)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # DELETE correct achievement (ours)
        response = self.client.delete(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # DELETE incorrect achievement (of another owner)
        url2 = reverse_lazy('rest_api:achievement-detail', kwargs={'uid': self.coach_ca.id, 'aid': achievement2.pk})
        response = self.client.delete(url2, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

