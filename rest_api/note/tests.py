from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from rest_framework import status

from multidb_account.constants import USER_TYPE_COACH, USER_TYPE_ATHLETE
from multidb_account.note.models import File, ReturnToPlayType, AthleteNote, CoachNote
from multidb_account.team.models import Team
from multidb_account.user.models import Coaching
from rest_api.tests import ApiTests

UserModel = get_user_model()


class FileTests(ApiTests):
    def test_files(self):
        user = self.coach_ca
        user2 = self.athlete_ca
        auth = 'JWT {}'.format(user.token)
        auth2 = 'JWT {}'.format(user2.token)
        url = reverse_lazy('rest_api:file-list')
        filepath = 'multidb_account/static/multidb_account/images/welcome-header.jpg'

        # Create a file by user1
        with open(filepath, 'rb') as f:
            data = {'file': f}
            response = self.client.post(url, data, format='multipart', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        file_id = response.data['id']
        file = File.objects.using(user.country).get(pk=file_id)
        self.assertEqual(response.data['owner'], user.id)

        # Create another file with the same name by user1
        with open(filepath, 'rb') as f:
            data = {'file': f}
            response = self.client.post(url, data, format='multipart', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner'], user.id)
        self.assertEqual(File.objects.using(user.country).count(), 2)

        url = reverse_lazy('rest_api:file-detail', kwargs={'pk': file_id})

        # DELETE file1 by user2 -> FAIL
        response = self.client.delete(url, HTTP_AUTHORIZATION=auth2)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        file.refresh_from_db()

        # DELETE correct file (ours)
        response = self.client.delete(url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class NoteTests(ApiTests):
    def create_coachnote(self, owner, athlete_id=None, team_id=None):
        url = reverse_lazy('rest_api:coachnote-list', kwargs={'uid': owner.id})
        auth = 'JWT {}'.format(owner.token)

        data = {
            'title': 'title1',
            'note': 'note1',
            'links': ['http://google.com', 'https://goo.gl'],
            'files': [],
        }

        if athlete_id:
            data['athlete_id'] = athlete_id
        elif team_id:
            data['team_id'] = team_id

        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.json())

        return CoachNote.objects.using(owner.country).get(pk=response.data['id'])

    def create_athletenote(self, owner, visible_to_coaches_ids=None, return_to_play_type=None):

        return_to_play_type = return_to_play_type or 'type1'

        auth = 'JWT {}'.format(owner.token)

        ReturnToPlayType.objects.using(owner.country).create(value=return_to_play_type)

        url = reverse_lazy('rest_api:athletenote-list', kwargs={'uid': owner.id})

        data = {
            'title': 'title1',
            'return_to_play_type': return_to_play_type,
            'note': 'note1'
        }

        if visible_to_coaches_ids is not None:
            data['only_visible_to'] = visible_to_coaches_ids

        # POST a note by the athlete
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)

        return AthleteNote.objects.using(owner.country).get(pk=response.data['id'])

    def test_athlete_notes(self):
        athlete = self.athlete_ca
        coach = self.coach_ca
        athlete_auth = 'JWT {}'.format(athlete.token)
        coach_auth = 'JWT {}'.format(coach.token)

        # Create a file by athlete
        file = File.objects.using(athlete.country).get(pk=self.upload_file(athlete).data['id'])
        file2 = File.objects.using(athlete.country).get(pk=self.upload_file(athlete).data['id'])

        # Create some ReturnToPlayType instances
        ReturnToPlayType.objects.using(athlete.country).create(value='type1')
        ReturnToPlayType.objects.using(athlete.country).create(value='type2')

        url = reverse_lazy('rest_api:athletenote-list', kwargs={'uid': athlete.id})
        data = {
            'title': 'title1',
            'return_to_play_type': 'type1',
            'links': ['http://google.com', 'https://goo.gl', 'www.helloworld.com',
                      'www.dfsdfsdfds.sd/sdfjsdfjds/sdfdsf-sdf/1.2/sdf/'],
            'files': [file.id, file2.id],
        }

        # POST with wrong return_to_play_type
        bad_data = data.copy()
        bad_data['return_to_play_type'] = 'type3'
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST with wrong links
        bad_data = data.copy()
        bad_data['links'] = '#!.,"'
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST with no links
        bad_data = data.copy()
        del bad_data['links']
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.json())

        # POST with empty links
        bad_data = data.copy()
        bad_data['links'] = []
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.json())

        # POST with wrong files
        bad_data = data.copy()
        bad_data['files'] = [-1, 0]
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST by a coach -> FAIL
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST a note by user1
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.json())

        note = AthleteNote.objects.using(athlete.country).get(pk=response.data['id'])
        self.assertEqual(note.title, data['title'])
        self.assertEqual({link.url for link in note.links.using(athlete.country)}, set(data['links']))
        self.assertEqual(note.return_to_play_type.value, data['return_to_play_type'])
        self.assertEqual({file.id for file in note.files.using(athlete.country)}, set(data['files']))

        # GET by user1
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        got_note = response.data[0]
        self.assertEqual(got_note['id'], note.id)
        self.assertEqual(got_note['owner'], athlete.id)
        self.assertEqual(got_note['note'], note.note)
        self.assertEqual({link for link in got_note['links']}, set(data['links']))
        self.assertEqual({file['id'] for file in got_note['files']}, set(data['files']))

        # PATCH note1 by owner
        patch_data = {
            'title': 'title2',
            'return_to_play_type': 'type2',
            'links': ['https://goo.gl'],
            'files': [file.id],
        }
        url = reverse_lazy('rest_api:athletenote-detail', kwargs={'uid': athlete.id, 'nid': note.id})
        response = self.client.patch(url, patch_data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        note.refresh_from_db()
        self.assertEqual(note.title, patch_data['title'])
        self.assertEqual({link.url for link in note.links.using(athlete.country)}, set(patch_data['links']))
        self.assertEqual(note.return_to_play_type.value, patch_data['return_to_play_type'])
        self.assertEqual({file.id for file in note.files.using(athlete.country)}, set(patch_data['files']))

        # DELETE correct note (ours)
        response = self.client.delete(url, HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # POST without return_to_play_type
        data2 = data.copy()
        data2.pop('return_to_play_type', None)
        url = reverse_lazy('rest_api:athletenote-list', kwargs={'uid': athlete.id})
        response = self.client.post(url, data2, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # POST without return_to_play_type #2
        data3 = data.copy()
        data3['return_to_play_type'] = ''
        url = reverse_lazy('rest_api:athletenote-list', kwargs={'uid': athlete.id})
        response = self.client.post(url, data3, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # POST without return_to_play_type #3
        data4 = data.copy()
        data4['return_to_play_type'] = None
        url = reverse_lazy('rest_api:athletenote-list', kwargs={'uid': athlete.id})
        response = self.client.post(url, data4, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_athlete_notes_permissions(self):
        athlete = self.athlete_ca
        coach = self.coach_ca
        athlete_auth = 'JWT {}'.format(athlete.token)
        coach_auth = 'JWT {}'.format(coach.token)
        bad_coach = self.create_random_user(country=athlete.country, user_type=USER_TYPE_COACH)
        bad_athlete = self.create_random_user(country=athlete.country, user_type=USER_TYPE_ATHLETE)
        bad_coach_auth = 'JWT {}'.format(bad_coach.token)
        bad_athlete_auth = 'JWT {}'.format(bad_athlete.token)

        # Create some ReturnToPlayType instances
        ReturnToPlayType.objects.using(athlete.country).create(value='type1')
        ReturnToPlayType.objects.using(athlete.country).create(value='type2')

        url = reverse_lazy('rest_api:athletenote-list', kwargs={'uid': athlete.id})
        data = {
            'title': 'title1',
            'return_to_play_type': 'type1',
            'note': 'note1',
            'only_visible_to': [coach.id],
        }

        # POST a note by the athlete
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        note = AthleteNote.objects.using(athlete.country).get(pk=response.data['id'])
        self.assertEqual(set(response.data['only_visible_to']), {coach.id})
        self.assertEqual(set(response.data['only_visible_to']),
                         {x.user.id for x in note.only_visible_to.using(athlete.country).all()})
        self.assertEqual(response.data['title'], data['title'])

        # GET a list of notes by the creator
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # GET a list of notes by the allowed coach
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # GET a list of notes by the bad coach
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=bad_coach_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        url = reverse_lazy('rest_api:athletenote-detail', kwargs={'uid': athlete.id, 'nid': note.id})

        # GET the note by creator
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(set(response.data['only_visible_to']), {coach.id})
        self.assertEqual(set(response.data['only_visible_to']),
                         {x.user.id for x in note.only_visible_to.using(athlete.country).all()})
        self.assertEqual(response.data['title'], data['title'])

        # GET the note by another coach
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=bad_coach_auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # GET the note by allowed coach
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], data['title'])

        # PATCH the note by another coach
        response = self.client.patch(url, format='json', HTTP_AUTHORIZATION=bad_coach_auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # PATCH the note by allowed coach
        response = self.client.patch(url, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # DELETE the note by another coach
        response = self.client.delete(url, format='json', HTTP_AUTHORIZATION=bad_coach_auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE the note by allowed coach
        response = self.client.delete(url, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # PATCH the note's `only_visible_to` by the creator
        data = {'only_visible_to': []}
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data['only_visible_to']), set())

        # GET the note by the former allowed coach
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET the note by the former disallowed coach
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=bad_coach_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET the note by the creator
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET the note by another athlete
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=bad_athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # PATCH the note by another athlete
        response = self.client.patch(url, format='json', HTTP_AUTHORIZATION=bad_athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_coach_notes(self):
        athlete = self.athlete_ca
        coach = self.coach_ca
        athlete_auth = 'JWT {}'.format(athlete.token)
        coach_auth = 'JWT {}'.format(coach.token)

        # Create a file by coach
        file = File.objects.using(coach.country).get(pk=self.upload_file(coach).data['id'])
        file2 = File.objects.using(coach.country).get(pk=self.upload_file(coach).data['id'])

        # Create some ReturnToPlayType instances
        ReturnToPlayType.objects.using(athlete.country).create(value='type1')
        ReturnToPlayType.objects.using(athlete.country).create(value='type2')

        # Create a team
        response = self.create_team(self.coach_ca)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.using(coach.country).get(id=response.data['id'])

        url = reverse_lazy('rest_api:coachnote-list', kwargs={'uid': coach.id})
        data = {
            'title': 'title1',
            'athlete_id': athlete.id,
            'links': ['http://google.com', 'https://goo.gl', 'www.helloworld.com'],
            'files': [file.id, file2.id],
        }

        # POST with wrong links
        bad_data = data.copy()
        bad_data['links'] = '#!.,"'
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST with no links
        bad_data = data.copy()
        del bad_data['links']
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # POST with empty links
        bad_data = data.copy()
        bad_data['links'] = []
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # POST with wrong files
        bad_data = data.copy()
        bad_data['files'] = [-1, 0]
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST with wrong athlete id
        bad_data = data.copy()
        bad_data['athlete_id'] = coach.id
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST with wrong team id
        bad_data = data.copy()
        bad_data['team_id'] = 0
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST with team id AND athlete id
        bad_data = data.copy()
        bad_data['team_id'] = team.id
        bad_data['athlete_id'] = athlete.id
        response = self.client.post(url, bad_data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST by an athlete -> FAIL
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST a note by user1
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.json())

        note = CoachNote.objects.using(coach.country).get(pk=response.data['id'])
        self.assertEqual(note.title, data['title'])
        self.assertEqual(note.athlete_id, data['athlete_id'])
        self.assertEqual({link.url for link in note.links.using(coach.country)}, set(data['links']))
        self.assertEqual({file.id for file in note.files.using(coach.country)}, set(data['files']))

        # GET by user1
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        got_note = response.data[0]
        self.assertEqual(got_note['id'], note.id)
        self.assertEqual(got_note['owner'], coach.id)
        self.assertIsNone(got_note['team_id'])
        self.assertEqual(got_note['athlete_id'], athlete.id)
        self.assertEqual({link for link in got_note['links']}, set(data['links']))
        self.assertEqual({file['id'] for file in got_note['files']}, set(data['files']))

        # PATCH note1 by owner
        data2 = {
            'team_id': team.id,
            'links': ['https://goo.gl'],
            'files': [file.id],
        }
        url = reverse_lazy('rest_api:coachnote-detail', kwargs={'uid': coach.id, 'nid': note.id})
        response = self.client.patch(url, data2, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        note.refresh_from_db()
        self.assertEqual(note.title, data['title'])
        self.assertEqual(note.team_id, data2['team_id'])
        self.assertEqual({link.url for link in note.links.using(coach.country)}, set(data2['links']))
        self.assertEqual({file.id for file in note.files.using(coach.country)}, set(data2['files']))

        # DELETE correct note (ours)
        response = self.client.delete(url, HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_return_to_play_type(self):
        athlete = self.athlete_ca
        athlete_auth = 'JWT {}'.format(athlete.token)

        # Create some ReturnToPlayType instances
        type1 = ReturnToPlayType.objects.using(athlete.country).create(value='type1')
        ReturnToPlayType.objects.using(athlete.country).create(value='type2')

        url = reverse_lazy('rest_api:return_to_play_type-list')

        # POST
        response = self.client.post(url, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # GET list
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 10)
        self.assertEqual(response.data[8]['value'], 'type1')

        url = reverse_lazy('rest_api:return_to_play_type-detail', kwargs={'pk': type1.pk})

        # PATCH
        response = self.client.patch(url, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # PUT
        response = self.client.put(url, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # DELETE
        response = self.client.delete(url, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_coach_notes_filter_by_athlete(self):
        athlete = self.athlete_ca
        athlete2 = self.create_random_user(country=athlete.country, user_type=USER_TYPE_ATHLETE)
        coach = self.coach_ca
        coach2 = self.create_random_user(country=coach.country, user_type=USER_TYPE_COACH)
        localized_db = coach.country
        coach_auth = 'JWT {}'.format(coach.token)

        # Create team with members
        response = self.create_team(owner=coach)
        team = Team.objects.using(localized_db).get(id=response.data['id'])
        team.athletes.add(athlete.athleteuser)
        team.coaches.add(coach.coachuser)

        # Create team2
        response = self.create_team(owner=coach)
        team2 = Team.objects.using(localized_db).get(id=response.data['id'])

        # Create coachnotes
        note_athlete_1 = self.create_coachnote(coach, athlete.id)
        note_athlete_2 = self.create_coachnote(coach2, athlete2.id)
        note_team_1 = self.create_coachnote(coach, team_id=team.id)
        self.create_coachnote(coach, team_id=team2.id)

        # GET by ahtlete1
        data = {'athlete_id': athlete.id}
        url = reverse_lazy('rest_api:all-coachnote-list')
        response = self.client.get(url, data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.json())
        got_ids = {x['id'] for x in response.data}
        self.assertEqual(got_ids, {note_athlete_1.id, note_team_1.id})

        # GET by ahtlete2
        data = {'athlete_id': athlete2.id}
        url = reverse_lazy('rest_api:all-coachnote-list')
        response = self.client.get(url, data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        got_ids = {x['id'] for x in response.data}
        self.assertEqual(got_ids, {note_athlete_2.id})

    def test_athlete_list_retrieved_by_coach(self):
        athlete = self.athlete_ca
        athlete2 = self.create_random_user(country=athlete.country, user_type=USER_TYPE_ATHLETE)
        coach = self.coach_ca
        coach2 = self.create_random_user(country=coach.country, user_type=USER_TYPE_COACH)
        localized_db = coach.country
        coach_auth = 'JWT {}'.format(coach.token)
        coach2_auth = 'JWT {}'.format(coach2.token)

        # Create coaching relations
        Coaching.objects.using(localized_db).create(
            athlete=athlete.athleteuser, coach=coach.coachuser)
        Coaching.objects.using(localized_db).create\
            (athlete=athlete2.athleteuser, coach=coach.coachuser)

        # Create team with members
        response = self.create_team(owner=coach)
        team = Team.objects.using(localized_db).get(id=response.data['id'])
        team.athletes.add(athlete.athleteuser)
        team.coaches.add(coach.coachuser)

        # create athletenotes
        self.create_athletenote(athlete, visible_to_coaches_ids=[coach.id],
                                return_to_play_type='type1')

        self.create_athletenote(athlete2, visible_to_coaches_ids=[coach.id],
                                return_to_play_type='type2')

        # this note is visible to all coaches because
        #  visible_to_coaches_ids == None
        self.create_athletenote(athlete, visible_to_coaches_ids=None,
                                return_to_play_type='type3')

        url = reverse_lazy('rest_api:all-athletes-list')

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(len(response.data), 3)

        response2 = self.client.get(url, format='json',
                                   HTTP_AUTHORIZATION=coach2_auth)

        self.assertEqual(len(response2.data), 0)

    def test_team_note_by_nonaccepted_athlete_account(self):
        athlete = self.athlete_ca
        athlete_auth = 'JWT {}'.format(athlete.token)
        coach = self.coach_ca
        coach_auth = 'JWT {}'.format(coach.token)
        localized_db = athlete.country

        # Create team
        response = self.create_team(owner=coach)
        team = Team.objects.using(localized_db).get(id=response.data['id'])

        # Invite athlete to the team
        response = self.invite_users(requester=coach, recipient=athlete, team_id=team.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Create a coach note for the team
        url = reverse_lazy('rest_api:coachnote-list', kwargs={'uid': coach.id})
        data = {
            'title': 'title1',
            'note': 'note1',
            'links': [],
            'files': [],
            'team_id': team.id,
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=coach_auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # GET all coachnotes by ahtlete
        url = reverse_lazy('rest_api:all-coachnote-list')
        response = self.client.get(url, data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # GET user coachnotes by ahtlete
        url = reverse_lazy('rest_api:coachnote-list', kwargs={'uid': coach.id})
        response = self.client.get(url, data, format='json', HTTP_AUTHORIZATION=athlete_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
