from django.core.urlresolvers import reverse_lazy
from model_mommy.mommy import make
from rest_framework import status

from multidb_account.constants import USER_TYPE_COACH
from multidb_account.sport.models import Sport
from multidb_account.team.models import Team
from rest_api.tests import ApiTests
from sport_engine.models import SportEngineTeam, SportEngineEvent


class SportEngineApiTests(ApiTests):

    def setUp(self):
        super().setUp()
        self.team = make(Team,
                         name='TheTeam',
                         sport=Sport.objects.last(),
                         athletes=[self.athlete.athleteuser],
                         owner=self.coach)
        self.se_team = make(SportEngineTeam, team=self.team)
        self.se_event = make(SportEngineEvent,
                             sport_engine_team=self.se_team,
                             sport_engine_game__sport_engine_teams=[self.se_team],
                             athletes=[self.athlete.athleteuser])

    def test_retrieve_events(self):
        # OK
        url = '%s?team_id=%i' % (reverse_lazy("rest_api:sportengine-event-list"), self.team.id)
        auth = 'JWT {}'.format(self.coach.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['sport_engine_id'], self.se_event.sport_engine_id)

        # FAIL: no team_id
        url = reverse_lazy("rest_api:sportengine-event-list")
        auth = 'JWT {}'.format(self.coach.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # FAIL: user not a member/owner -> no data
        alien_coach = self.create_random_user(country='default', user_type=USER_TYPE_COACH)
        url = '%s?team_id=%i' % (reverse_lazy("rest_api:sportengine-event-list"), self.team.id)
        auth = 'JWT {}'.format(alien_coach.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_retrieve_games(self):
        # OK
        url = '%s?team_id=%i' % (reverse_lazy("rest_api:sportengine-game-list"), self.team.id)
        auth = 'JWT {}'.format(self.coach.token)
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['sport_engine_id'], self.se_event.sport_engine_game.sport_engine_id)
