from datetime import timedelta
from unittest import mock

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from rest_framework import status

from multidb_account.assessment.models import AssessmentTopCategoryPermission
from multidb_account.constants import USER_TYPE_ATHLETE, USER_TYPE_COACH, INVITE_ACCEPTED, INVITE_CANCELED
from multidb_account.invite.models import Invite
from multidb_account.user.models import Coaching
from multidb_account.team.models import Team

from rest_api.tests import ApiTests

UserModel = get_user_model()


class InviteTests(ApiTests):

    def test_invites_revoke_after_confirmation(self):
        localized_db = self.coach_ca.country

        # Invite athlete by coach
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email text'
            response = self.invite_users(requester=self.coach_ca, recipient=self.athlete_ca)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token = mock_render_to_string.call_args_list[0][0][1]['token']

        # Check created invite
        invite = Invite.objects.using(localized_db).order_by('pk').last()
        self.assertEqual(invite.requester, self.coach_ca)
        self.assertEqual(invite.recipient, self.athlete_ca.email)

        # Confirm
        response = self.confirm_invite(token, self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check Coaching was created
        self.assertTrue(Coaching.objects.using(localized_db).filter(
            athlete=self.athlete_ca.athleteuser, coach=self.coach_ca.coachuser
        ).exists())

        # Cancel it by recipient
        response = self.revoke_invites_by_user(
            revoker=self.coach_ca, revokee_email=self.athlete_ca.email)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check Coaching was removed
        self.assertFalse(Coaching.objects.using(localized_db).filter(
            athlete=self.athlete_ca.athleteuser, coach=self.coach_ca.coachuser
        ).exists())

    def test_invite_not_registered(self):
        localized_db = self.coach_ca.country  # Save initial invite records count
        recipient_email = 'test@test.com'
        # Invite athlete by coach

        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email text'
            response = self.invite_users(requester=self.coach_ca,
                                         recipient_email=recipient_email,
                                         recipient_type='athlete')
            token = mock_render_to_string.call_args_list[0][0][1]['token']
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check created invite
        invite = Invite.objects.using(localized_db).order_by('pk').last()
        self.assertEqual(invite.requester, self.coach_ca)
        self.assertEqual(invite.recipient, recipient_email)

    def test_invites(self):
        localized_db = self.coach_ca.country  # Save initial invite records count
        invite_count = Invite.objects.using(localized_db).count()

        # Invite athlete by coach
        response = self.invite_users(requester=self.coach_ca, recipient=self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check created invite
        invite = Invite.objects.using(localized_db).order_by('pk').last()
        self.assertEqual(invite.requester, self.coach_ca)
        self.assertEqual(invite.recipient, self.athlete_ca.email)
        self.assertEqual(invite.recipient_type, self.athlete_ca.user_type)

        # Try to invite for the 2nd time when there's a non-expired previous invite -> FAIL
        response = self.invite_users(requester=self.coach_ca, recipient=self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Move date_sent of the first invite to the distant past
        expired_invite = invite
        expired_minus_5_mins = expired_invite.date_sent - timedelta(
            seconds=django_settings.USER_INVITE_TOKEN_EXPIRES) - timedelta(minutes=5)

        expired_invite.date_sent = expired_minus_5_mins
        expired_invite.save(update_fields=('date_sent',))

        # Try to confirm the expired invate -> FAIL
        response = self.confirm_invite(expired_invite.invite_token_hash, self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Try to invite for the 3rd time when there's an expired previous invite -> OK
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email text'
            response = self.invite_users(requester=self.coach_ca, recipient=self.athlete_ca)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token = mock_render_to_string.call_args_list[0][0][1]['token']

        # Confirm the 3rd invite -> OK
        confirmed_invite = Invite.objects.using(localized_db).order_by('pk').last()
        response = self.confirm_invite(token, self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check accepted invite's status
        confirmed_invite.refresh_from_db()
        self.assertEqual(confirmed_invite.status, INVITE_ACCEPTED)

        # Try to invite user who's just confirmed another invite -> FAIL
        response = self.invite_users(requester=self.coach_ca, recipient=self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Check total invite records count
        self.assertEqual(Invite.objects.using(localized_db).count(), invite_count + 2)

    def test_invite_revoke_by_user(self):
        localized_db = self.coach_ca.country

        # Save initial invite records count
        invite_count = Invite.objects.using(localized_db).count()

        # 1. Invite coach by athlete
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email value'
            response = self.invite_users(requester=self.athlete_ca, recipient=self.coach_ca)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token = mock_render_to_string.call_args_list[0][0][1]['token']

        # Check created invite
        revoked_by_requester = Invite.objects.using(localized_db).order_by('pk').last()
        self.assertEqual(revoked_by_requester.requester, self.athlete_ca)
        self.assertEqual(revoked_by_requester.recipient, self.coach_ca.email)

        # Cancel it by requester
        response = self.revoke_invites_by_user(revoker=self.athlete_ca, revokee_email=revoked_by_requester.recipient)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check canceled invite's status
        revoked_by_requester.refresh_from_db()
        self.assertEqual(revoked_by_requester.status, INVITE_CANCELED)

        # Check if we can use revoked invite
        response = self.confirm_invite(token=token, confirmer=self.coach_ca)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Invite athlete by coach
        response = self.invite_users(requester=self.coach_ca, recipient=self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check created invite
        revoked_by_recipient = Invite.objects.using(localized_db).order_by('pk').last()
        self.assertEqual(revoked_by_recipient.requester, self.coach_ca)
        self.assertEqual(revoked_by_recipient.recipient, self.athlete_ca.email)

        # Cancel it by recipient
        response = self.revoke_invites_by_user(revoker=self.coach_ca, revokee_email=revoked_by_recipient.recipient)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check canceled invite's status
        revoked_by_recipient.refresh_from_db()
        self.assertEqual(revoked_by_recipient.status, INVITE_CANCELED)

        # 3. Try to invite for the 3rd time when there are canceled previous invites exist -> FAIL (too soon)
        response = self.invite_users(requester=self.coach_ca, recipient=self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Move date_sent of the previous invites to the past
        old_revoked_by_requester = revoked_by_requester
        timeout_minus_5_mins = old_revoked_by_requester.date_sent - timedelta(
            seconds=django_settings.USER_INVITE_TIMEOUT) - timedelta(minutes=5)

        old_revoked_by_requester.date_sent = timeout_minus_5_mins
        old_revoked_by_requester.save(update_fields=('date_sent',))

        old_revoked_by_recipient = revoked_by_recipient
        old_revoked_by_recipient.date_sent = timeout_minus_5_mins
        old_revoked_by_recipient.save(update_fields=('date_sent',))

        # 4. Try to invite for the 4th time when there are old canceled previous invites exist -> OK
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email value'
            response = self.invite_users(requester=self.coach_ca, recipient=self.athlete_ca)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token3 = mock_render_to_string.call_args_list[0][0][1]['token']

        # Confirm the 3rd invite -> OK
        confirmed_invite = Invite.objects.using(localized_db).order_by('pk').last()
        response = self.confirm_invite(token=token3, confirmer=self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check accepted invite's status
        confirmed_invite.refresh_from_db()
        self.assertEqual(confirmed_invite.status, INVITE_ACCEPTED)

        # 4. Check total invite records count
        self.assertEqual(Invite.objects.using(localized_db).count(), invite_count + 3)

    def test_invite_to_team(self):
        localized_db = self.coach_ca.country

        # Create a team
        response = self.create_team(self.coach_ca)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.using(localized_db).get(id=response.data['id'])

        # Save initial invite records count
        invite_count = Invite.objects.using(localized_db).count()

        # Invite athlete by coach to an invalid team
        response = self.invite_users(requester=self.coach_ca, recipient=self.athlete_ca, team_id=-1)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invite athlete by coach to a valid team

        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email text'
            response = self.invite_users(requester=self.coach_ca, recipient=self.athlete_ca, team_id=team.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token = mock_render_to_string.call_args_list[0][0][1]['token']

        # Check created invite
        invite = Invite.objects.using(localized_db).order_by('pk').last()
        self.assertEqual(invite.requester, self.coach_ca)
        self.assertEqual(invite.recipient, self.athlete_ca.email)
        self.assertEqual(invite.team, team)

        # Check that recipient isn't yet a part of the team
        self.assertNotIn(self.athlete_ca.athleteuser, team.athletes.using(localized_db).all())

        # Confirm the invite
        response = self.confirm_invite(token=token, confirmer=self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that recipient is now a part of the team
        self.assertIn(self.athlete_ca.athleteuser, team.athletes.using(localized_db).all())

        # Check total invite records count
        self.assertEqual(Invite.objects.using(localized_db).count(), invite_count + 1)

        auth = 'JWT {}'.format(self.coach_ca.token)
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.coach_ca.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(dict(response.data.get('linked_users')[0]).get('id'), self.athlete_ca.id)
        self.assertEqual(dict(response.data.get('linked_users')[0]).get('email'), self.athlete_ca.email)
        self.assertEqual(dict(response.data.get('linked_users')[0]).get('user_type'), USER_TYPE_ATHLETE)
        self.assertEqual(dict(response.data.get('linked_users')[0]).get('first_name'), self.athlete_ca.first_name)
        self.assertEqual(dict(response.data.get('linked_users')[0]).get('last_name'), self.athlete_ca.last_name)

        auth = 'JWT {}'.format(self.athlete_ca.token)
        url = reverse_lazy('rest_api:user-detail', kwargs={'uid': self.athlete_ca.id})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(dict(response.data.get('linked_users')[0]).get('id'), self.coach_ca.id)
        self.assertEqual(dict(response.data.get('linked_users')[0]).get('email'), self.coach_ca.email)
        self.assertEqual(dict(response.data.get('linked_users')[0]).get('user_type'), USER_TYPE_COACH)
        self.assertEqual(dict(response.data.get('linked_users')[0]).get('first_name'), self.coach_ca.first_name)
        self.assertEqual(dict(response.data.get('linked_users')[0]).get('last_name'), self.coach_ca.last_name)

    def test_invite_to_org_team(self):
        localized_db = self.coach_ca.country

        # Create a team
        response = self.create_team(self.coach_ca)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.using(localized_db).get(id=response.data['id'])
        team.organisation = self.org_ca.organisation
        team.owner = self.org_ca
        team.save()

        # Invite athlete by org to a valid team
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email text'
            response = self.invite_users(requester=self.org_ca, recipient=self.athlete_ca, team_id=team.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token = mock_render_to_string.call_args_list[0][0][1]['token']

        # Confirm the invite
        response = self.confirm_invite(token=token, confirmer=self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that recipient is now a part of the team
        self.assertIn(self.athlete_ca.athleteuser, team.athletes.using(localized_db).all())

        # Check that coach-athlete permissions are set
        permissions = AssessmentTopCategoryPermission.objects.using(localized_db) \
            .filter(assessed=self.athlete_ca.get_assessed(), assessor=self.coach_ca.get_assessor())
        self.assertTrue(permissions.exists())

    def test_invite_many(self):
        localized_db = self.coach_ca.country

        # Create second athlete
        athlete_ca2 = self.create_random_user(country=self.coach_ca.country, user_type=USER_TYPE_ATHLETE)

        # Create a team
        response = self.create_team(self.coach_ca)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.using(localized_db).get(id=response.data['id'])

        # Save initial invite records count
        invite_count = Invite.objects.using(localized_db).count()

        # Invite athlete by coach to a team
        # mock it to extract token from email
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email content'
            response = self.invite_users(requester=self.coach_ca, recipients=[self.athlete_ca, athlete_ca2],
                                         team_id=team.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token_for_athlete_ca = mock_render_to_string.call_args_list[0][0][1]['token']

        # Check created invite
        invite2 = Invite.objects.using(localized_db).order_by('pk').last()
        self.assertEqual(invite2.requester, self.coach_ca)
        self.assertEqual(invite2.recipient, athlete_ca2.email)
        self.assertEqual(invite2.team, team)

        invite = Invite.objects.using(localized_db).exclude(id=invite2.id).order_by('pk').last()
        self.assertEqual(invite.requester, self.coach_ca)
        self.assertEqual(invite.recipient, self.athlete_ca.email)
        self.assertEqual(invite.team, team)

        # Check that recipients aren't yet a part of the team
        self.assertNotIn(self.athlete_ca.athleteuser, team.athletes.using(localized_db).all())
        self.assertNotIn(athlete_ca2.athleteuser, team.athletes.using(localized_db).all())

        # Confirm the first invite
        response = self.confirm_invite(token=token_for_athlete_ca, confirmer=self.athlete_ca)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the first recipient is now a part of the team
        self.assertIn(self.athlete_ca.athleteuser, team.athletes.using(localized_db).all())

        # Check that the second recipient is not a part of the team
        self.assertNotIn(athlete_ca2.athleteuser, team.athletes.using(localized_db).all())

        # Check total invite records count
        self.assertEqual(Invite.objects.using(localized_db).count(), invite_count + 2)

    def test_invite_many_some_rejected(self):
        localized_db = self.coach_ca.country

        # Create second athlete
        athlete_ca2 = self.create_random_user(country=self.coach_ca.country, user_type=USER_TYPE_ATHLETE)

        # Create a team
        response = self.create_team(self.coach_ca)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.using(localized_db).get(id=response.data['id'])

        # Save initial invite records count
        invite_count = Invite.objects.using(localized_db).count()

        # Invite #1 athlete by coach to a team
        # Mock it to extract token from email
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email content'
            response = self.invite_users(requester=self.coach_ca,
                                         recipients=[self.athlete_ca],
                                         team_id=team.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Invite #2 athletes by coach to a team
        # One of them is already invited => return 200 since some the invites are new
        response = self.invite_users(requester=self.coach_ca,
                                     recipients=[self.athlete_ca, athlete_ca2],
                                     team_id=team.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # There's info about emails that failed validation
        self.assertEqual(response.data['errors'][0],
                         {self.athlete_ca.email: ['Another pending non-expired invite already exists.']})

        # Check total invite records count
        self.assertEqual(Invite.objects.using(localized_db).count(), invite_count + 2)

        # Invite #3 athletes by coach to a team
        # All of them are already invited => return 400
        response = self.invite_users(requester=self.coach_ca,
                                     recipients=[self.athlete_ca, athlete_ca2],
                                     team_id=team.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # There's info about emails that failed validation
        self.assertEqual(response.data, [
            {self.athlete_ca.email: ['Another pending non-expired invite already exists.']},
            {athlete_ca2.email: ['Another pending non-expired invite already exists.']},
        ])
        # Check total invite records count
        self.assertEqual(Invite.objects.using(localized_db).count(), invite_count + 2)

    def test_invite_to_team_coach_invites_another_coach(self):
        localized_db = self.coach_ca.country

        # Create a team
        response = self.create_team(self.coach_ca)

        team = Team.objects.using(localized_db).get(id=response.data['id'])

        # Create another coach
        recipient_coach = self.create_random_user(country='ca',
                                                  user_type=USER_TYPE_COACH)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Save initial invite records count
        invite_count = Invite.objects.using(localized_db).count()

        # Invite coach by coach to an invalid team
        response = self.invite_users(requester=self.coach_ca, recipient=recipient_coach, team_id=-1)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invite athlete by coach to a valid team

        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email text'
            response = self.invite_users(requester=self.coach_ca, recipient=recipient_coach, team_id=team.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token = mock_render_to_string.call_args_list[0][0][1]['token']

        # Check created invite
        invite = Invite.objects.using(localized_db).order_by('pk').last()
        self.assertEqual(invite.requester, self.coach_ca)
        self.assertEqual(invite.recipient, recipient_coach.email)
        self.assertEqual(invite.team, team)

        # Check that recipient isn't yet a part of the team
        self.assertNotIn(recipient_coach.coachuser, team.coaches.using(localized_db).all())

        # Confirm the invite
        response = self.confirm_invite(token=token, confirmer=recipient_coach)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.json())

        # Check that recipient is now a part of the team
        self.assertIn(recipient_coach.coachuser, team.coaches.using(localized_db).all())

        # Check total invite records count
        self.assertEqual(Invite.objects.using(localized_db).count(), invite_count + 1)

    def test_user_pending_invite_list(self):
        user = self.coach_ca
        localized_db = user.country

        # Create second athlete
        athlete_ca2 = self.create_random_user(country=user.country, user_type=USER_TYPE_ATHLETE)

        # Create a team
        response = self.create_team(user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.using(localized_db).get(id=response.data['id'])

        # Invite athlete by coach to a team
        # mock it to extract token from email
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email content'
            response = self.invite_users(requester=user, recipients=[self.athlete_ca], team_id=team.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            invite1_token = mock_render_to_string.call_args_list[0][0][1]['token']

        # Invite athlete without team
        response = self.invite_users(requester=user, recipient=athlete_ca2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invite2 = Invite.objects.using(localized_db).order_by('pk').last()

        # # GET inviter's invite list with 2 invites pending
        response = self.get_user_pending_invites(user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        resp_invite1 = response.data[0]
        self.assertEqual(resp_invite1['requester_id'], user.id)
        self.assertEqual(resp_invite1['recipient'], self.athlete_ca.email)
        self.assertEqual(resp_invite1['team_id'], team.id)

        resp_invite2 = response.data[1]
        self.assertEqual(resp_invite2['requester_id'], user.id)
        self.assertEqual(resp_invite2['recipient'], athlete_ca2.email)
        self.assertIsNone(resp_invite2['team_id'])

        # GET invite list of the first invitee => empty because he can't see invites of himself
        response = self.get_user_pending_invites(self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # GET list of the second invitee  => empty because he can't see invites of himself
        response = self.get_user_pending_invites(athlete_ca2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # # Confirm the first invite
        response = self.confirm_invite(token=invite1_token, confirmer=self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # # GET inviter's invite list #2 with only 1 invite pending
        response = self.get_user_pending_invites(user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        resp_invite2 = response.data[0]
        self.assertEqual(resp_invite2['requester_id'], user.id)
        self.assertEqual(resp_invite2['recipient'], athlete_ca2.email)
        self.assertIsNone(resp_invite2['team_id'])

        # GET invite list of the first invitee
        response = self.get_user_pending_invites(self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # GET invite list of the second invitee  => empty because he can't see invites of himself
        response = self.get_user_pending_invites(athlete_ca2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # # Cancel the second invite
        response = self.revoke_invites_by_user(revoker=user, revokee_email=invite2.recipient)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # # GET inviter's invite list #3 with no invites pending
        response = self.get_user_pending_invites(user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # GET list of the first invitee
        response = self.get_user_pending_invites(self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # GET list of the second invitee
        response = self.get_user_pending_invites(athlete_ca2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_team_pending_invite_list(self):
        user = self.coach_ca
        localized_db = user.country

        # Create more athletes
        athlete_ca2 = self.create_random_user(country=user.country, user_type=USER_TYPE_ATHLETE)
        athlete_ca3 = self.create_random_user(country=user.country, user_type=USER_TYPE_ATHLETE)

        # Create a team
        response = self.create_team(user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.using(localized_db).get(id=response.data['id'])

        # Create another team
        response = self.create_team(user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team2 = Team.objects.using(localized_db).get(id=response.data['id'])

        # Invite athlete by coach to team1
        # mock it to extract token from email
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email content'
            response = self.invite_users(requester=user, recipients=[self.athlete_ca], team_id=team.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            invite1_token = mock_render_to_string.call_args_list[0][0][1]['token']

        # Invite another athlete by coach to team2
        response = self.invite_users(requester=user, recipients=[athlete_ca2], team_id=team2.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Invite third athlete without team
        response = self.invite_users(requester=user, recipient=athlete_ca3)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET team1 invite list with 1 invite pending
        response = self.get_team_pending_invites(user, team.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        resp_invite1 = response.data[0]
        self.assertEqual(resp_invite1['requester_id'], user.id)
        self.assertEqual(resp_invite1['recipient'], self.athlete_ca.email)
        self.assertEqual(resp_invite1['team_id'], team.id)

        # GET team2 invite list with 1 invite pending
        response = self.get_team_pending_invites(user, team2.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        resp_invite2 = response.data[0]
        self.assertEqual(resp_invite2['requester_id'], user.id)
        self.assertEqual(resp_invite2['recipient'], athlete_ca2.email)
        self.assertEqual(resp_invite2['team_id'], team2.id)

        # # Confirm the first invite
        response = self.confirm_invite(token=invite1_token, confirmer=self.athlete_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # # GET team1 invite list with no pending invites
        response = self.get_team_pending_invites(user, team.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # # GET team2 invite list with (still) 1 invite pending
        response = self.get_team_pending_invites(user, team2.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        resp_invite2 = response.data[0]
        self.assertEqual(resp_invite2['requester_id'], user.id)
        self.assertEqual(resp_invite2['recipient'], athlete_ca2.email)
        self.assertEqual(resp_invite2['team_id'], team2.id)

        # # Cancel the second invite
        response = self.revoke_invites_by_user(revoker=user, revokee_email=athlete_ca2.email)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET team1 invite list with no pending invites
        response = self.get_team_pending_invites(user, team.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # GET team2 invite list with no pending invites
        response = self.get_team_pending_invites(user, team2.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_invite_revoke_single_or_multiple(self):
        localized_db = self.coach_ca.country

        # Save initial invite records count
        invite_count = Invite.objects.using(localized_db).count()

        # Create more users
        athlete_ca2 = self.create_random_user(country=self.coach_ca.country, user_type=USER_TYPE_ATHLETE)
        coach_ca2 = self.create_random_user(country=self.coach_ca.country, user_type=USER_TYPE_COACH)
        coach_ca3 = self.create_random_user(country=self.coach_ca.country, user_type=USER_TYPE_COACH)
        coach_ca4 = self.create_random_user(country=self.coach_ca.country, user_type=USER_TYPE_COACH)
        coach_ca5 = self.create_random_user(country=self.coach_ca.country, user_type=USER_TYPE_COACH)

        # Invite coach1 by athlete1
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email value'
            response = self.invite_users(requester=self.athlete_ca, recipient=self.coach_ca)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token1 = mock_render_to_string.call_args_list[0][0][1]['token']
        invite1 = Invite.objects.using(localized_db).order_by('pk').last()

        # Invite coach2 by athlete1
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email value'
            response = self.invite_users(requester=self.athlete_ca, recipient=coach_ca2)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token2 = mock_render_to_string.call_args_list[0][0][1]['token']
        invite2 = Invite.objects.using(localized_db).order_by('pk').last()

        # Invite coach3 by athlete1
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email value'
            response = self.invite_users(requester=self.athlete_ca, recipient=coach_ca3)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token3 = mock_render_to_string.call_args_list[0][0][1]['token']
        invite3 = Invite.objects.using(localized_db).order_by('pk').last()

        # Invite athlete2 by coach1
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email value'
            response = self.invite_users(requester=self.coach_ca, recipient=athlete_ca2)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token4 = mock_render_to_string.call_args_list[0][0][1]['token']
        invite4 = Invite.objects.using(localized_db).order_by('pk').last()

        # Invite coach4 by athlete1
        response = self.invite_users(requester=self.athlete_ca, recipient=coach_ca4)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invite5 = Invite.objects.using(localized_db).order_by('pk').last()

        # Invite coach5 by athlete1
        response = self.invite_users(requester=self.athlete_ca, recipient=coach_ca5)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invite6 = Invite.objects.using(localized_db).order_by('pk').last()

        # 1. Cancel first invite by id as athlete_ca (inviter)
        response = self.revoke_invite_by_token(revoker=self.athlete_ca, id_=invite1.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check canceled invite's status
        invite1.refresh_from_db()
        self.assertEqual(invite1.status, INVITE_CANCELED)

        # Check if we can use revoked invite
        response = self.confirm_invite(token=token1, confirmer=self.coach_ca)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Cancel invites by their ids as athlete_ca (inviter)
        response = self.revoke_invite_by_token(revoker=self.athlete_ca, ids=[invite5.id, invite6.id])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check canceled invite's status
        invite1.refresh_from_db()
        self.assertEqual(invite1.status, INVITE_CANCELED)

        # Check if we can use revoked invite
        response = self.confirm_invite(token=token1, confirmer=self.coach_ca)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Cancel multiple invites by athlete_ca (inviter)
        response = self.revoke_invite_by_token(revoker=self.athlete_ca, tokens=[token2, token3])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check canceled invite's status
        invite2.refresh_from_db()
        self.assertEqual(invite2.status, INVITE_CANCELED)

        invite3.refresh_from_db()
        self.assertEqual(invite3.status, INVITE_CANCELED)

        # Check if we can use revoked invite
        response = self.confirm_invite(token=token2, confirmer=coach_ca2)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.confirm_invite(token=token3, confirmer=coach_ca3)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Cancel last invite by athlete_ca2 (recipient)
        response = self.revoke_invite_by_token(revoker=athlete_ca2, token=token4)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check canceled invite's status
        invite4.refresh_from_db()
        self.assertEqual(invite4.status, INVITE_CANCELED)

        # Check if we can use revoked invite
        response = self.confirm_invite(token=token4, confirmer=athlete_ca2)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 5. Check total invite records count
        self.assertEqual(Invite.objects.using(localized_db).count(), invite_count + 6)

    def test_invite_resend(self):
        localized_db = self.coach_ca.country
        athlete_ca2 = self.create_random_user(country=self.athlete_ca.country, user_type=USER_TYPE_ATHLETE)
        coach_ca2 = self.create_random_user(country=self.coach_ca.country, user_type=USER_TYPE_COACH)

        # Invite coach1 by athlete1
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email value'
            response = self.invite_users(requester=self.athlete_ca, recipient=self.coach_ca)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token = mock_render_to_string.call_args_list[0][0][1]['token']
        invite = Invite.objects.using(localized_db).order_by('pk').last()

        # Invite coach2 by athlete1
        response = self.invite_users(requester=athlete_ca2, recipient=coach_ca2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invite2 = Invite.objects.using(localized_db).order_by('pk').last()

        url = reverse_lazy('rest_api:users-invite-resend')
        auth = 'JWT {}'.format(self.athlete_ca.token)

        # Resend the incorrect invite id
        data = {'id': invite2.id}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Resend the incorrect invite id #2
        data = {'id': 0}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Resend the incorrect invite id #3
        data = {'id': 'not an int'}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = {'id': invite.id}

        # Resend the correct invite as incorrect user
        auth = 'JWT {}'.format(coach_ca2.token)
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Resend the correct invite as incorrect user #2
        auth = 'JWT {}'.format(athlete_ca2.token)
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Try to resend the invite with no .recipient_type
        recipient_type = invite.recipient_type
        invite.recipient_type = None
        invite.save()

        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Wait 1 sec to ensure that token's timestamp doesn't break it
        import time
        time.sleep(1)

        # Resend the invite
        invite.recipient_type = recipient_type
        invite.save()

        auth = 'JWT {}'.format(self.athlete_ca.token)

        # Resend the correct invite as correct user -> FAIL (too soon)
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Move date_sent of the previous invite to the past
        timeout_minus_5_mins = invite.date_sent - timedelta(
            seconds=django_settings.USER_INVITE_TIMEOUT) - timedelta(minutes=5)

        invite.date_sent = timeout_minus_5_mins
        invite.save(update_fields=('date_sent',))

        # Success
        with mock.patch('multidb_account.invite.models.loader.render_to_string') as mock_render_to_string:
            mock_render_to_string.return_value = 'some email value'
            response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            token2 = mock_render_to_string.call_args_list[0][0][1]['token']

        # Confirm the invite
        response = self.confirm_invite(token=token2, confirmer=self.coach_ca)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
