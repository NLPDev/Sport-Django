from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers, exceptions

from multidb_account.constants import USER_TYPE_COACH, USER_TYPE_ATHLETE, INVITE_ACCEPTED, INVITE_CANCELED, \
    INVITE_PENDING, USER_TYPE_ORG
from multidb_account.user.models import Coaching
from multidb_account.invite.models import Invite
from multidb_account.assessment.models import AssessmentTopCategory, AssessmentTopCategoryPermission
from multidb_account.team.models import Team

from rest_api.mixins import ValidateInviteTokenMixin

UserModel = get_user_model()


class UserInviteSerializer(serializers.Serializer):
    """
    Serializer for user connection request endpoint.
    """

    recipient = serializers.EmailField(required=True)
    team_id = serializers.IntegerField(required=False)
    recipient_type = serializers.CharField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = None
        self.custom_validated_data = []  # Keep the `.validated_data` for non-errored objects when `many=True`

    def validate_team_id(self, value):
        self.team = Team.objects.using(self.context['request'].user.country).filter(id=value).first()
        if not self.team:
            raise serializers.ValidationError(_("Team id is not valid."))
        return value

    def validate(self, data):
        requester = self.context['request'].user
        localized_db = requester.country
        recipient_email = data.get('recipient')

        if Invite.objects.pending_nonexpired().using(localized_db) \
                .filter(requester=requester, recipient=recipient_email).exists():
            raise serializers.ValidationError({
                recipient_email: _('Another pending non-expired invite already exists.')
            })

        self.custom_validated_data.append(data)
        return data

    def create(self, validated_data):
        recipient_email = validated_data.get('recipient')
        recipient_type = validated_data.get('recipient_type')

        team_id = validated_data.get('team_id')
        team = self.team if team_id else None

        requester = self.context['request'].user
        localized_db = requester.country

        # User can not send invite to himself
        if recipient_email == requester.email:
            raise exceptions.ParseError(
                _('You can not send invite you yourself'))

        # Check for previous non-expired invites
        if Invite.objects.pending_nonexpired().using(localized_db) \
                .filter(requester=requester, recipient=recipient_email).exists():
            raise exceptions.ParseError(
                _('Another pending non-expired invite already exists.'))

        # Don't invite users already participating in team
        if team is not None and requester.user_type == USER_TYPE_ATHLETE \
                and team.athletes.filter(user__email=recipient_email).exists():
            raise exceptions.ParseError(
                _('Athlete with email {recipient_email} '
                  'already participates in team'))

        if team is not None and requester.user_type == USER_TYPE_COACH and \
                (team.coaches.filter(user__email=recipient_email).exists() or team.owner.email == recipient_email):
            raise exceptions.ParseError(
                _('Coach with email {recipient_email} '
                  'already participates in team'))

        # Don't invite already connected users
        if team is None and recipient_type != requester.user_type:
            if requester.user_type == USER_TYPE_COACH and Coaching.objects.using(localized_db).filter(
                    athlete__user__email=recipient_email, coach__user=requester).exists():
                raise exceptions.ParseError(
                    _('Users have been already connected.'))

            elif requester.user_type == USER_TYPE_ATHLETE and Coaching.objects.using(localized_db).filter(
                    athlete__user=requester, coach__user__email=recipient_email).exists():
                raise exceptions.ParseError(
                    _('Users have been already connected.'))

        # Don't invite when there are previous invites newer than
        # USER_INVITE_TIMEOUT
        if Invite.objects.recent().using(localized_db) \
                .filter(requester=requester, recipient=recipient_email, team=team).exists():
            raise exceptions.ParseError(
                _('Too frequent invitation requests. Please try again later.'))

        token, token_hash = Invite.make_token(requester, recipient_email, recipient_type)

        # Create an invite
        invite = Invite.objects.using(localized_db).create(
            requester=requester,
            invite_token_hash=token_hash,
            status=INVITE_PENDING,
            recipient=recipient_email,
            recipient_type=recipient_type,
            team_id=team_id,
        )

        invite.send_email(token)
        return invite


class UserInviteResendSerializer(serializers.Serializer):
    """
    Serializer to resend user invite to connect.
    """

    id = serializers.IntegerField(required=True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Invite

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.invite = None

    def validate(self, attrs):
        user = attrs['user']
        localized_db = user.country

        try:
            self.invite = Invite.objects.using(localized_db).get(pk=attrs['id'])
        except Invite.DoesNotExist:
            raise serializers.ValidationError({"id": "Unknown invite id."})

        if self.invite.requester != user:
            raise serializers.ValidationError({"id": "Current user isn't the creator of this invite."})

        if self.invite.recipient_type is None:
            raise serializers.ValidationError({"id": "This invite can't be resent. No recipient_type."})

        # Don't invite when there are previous invites newer than
        # USER_INVITE_TIMEOUT
        if Invite.objects.recent().using(localized_db).filter(
                requester=self.invite.requester,
                recipient=self.invite.recipient,
                team=self.invite.team
        ).exists():
            raise exceptions.ParseError(
                _('Too frequent invitation requests. Please try again later.'))

        return super().validate(attrs)

    def save(self):
        self.invite.send_email()
        return True

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class UserInviteConfirmSerializer(ValidateInviteTokenMixin, serializers.Serializer):
    """
    Serializer for user connection confirmation endpoint.
    """
    # only used for reset(write)
    user_invite_token = serializers.CharField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.invite = self.recipient = self.requester = self.localized_db = None

    def validate_user_invite_token(self, token):
        return super().validate_user_invite_token(token)

    def save(self):
        athlete = coach = None

        # athlete invites athlete or coach invites coach. Do nothing!
        if self.invite.team is None and self.invite.requester.user_type == self.recipient.user_type:
            return {'requester_first_name': self.requester.first_name,
                    'requester_last_name': self.requester.last_name,
                    'requester_id': self.requester.id,
                    'requester_type': self.requester.user_type}

        # Change invite's status to INVITE_ACCEPTED
        self.invite.status = INVITE_ACCEPTED
        self.invite.save(update_fields=('status',))

        if self.recipient.user_type not in (USER_TYPE_ATHLETE, USER_TYPE_COACH):
            raise serializers.ValidationError(_("Could not invite organisation accounts."))

        if self.requester.user_type != self.recipient.user_type and self.requester.user_type != USER_TYPE_ORG:
            athlete = self.recipient.athleteuser if self.recipient.user_type == USER_TYPE_ATHLETE else self.requester.athleteuser
            coach = self.recipient.coachuser if self.recipient.user_type == USER_TYPE_COACH else self.requester.coachuser

        # Activate new dashboard UI for the invited users
        # self.recipient.new_dashboard = True
        # self.recipient.save(update_fields=['new_dashboard'])

        # Add recipient to the team specified
        if self.invite.team:
            self.invite.team.add_baseuser(self.recipient)

        if athlete and coach:
            Coaching.create_if_not_exist(self.localized_db, athlete, coach)

        for top_category in AssessmentTopCategory.objects.using(self.localized_db).all():
            # we want all top categories granted by default to Coaches
            # we want category (general-leadership(id=10001)) granted by default to athlete
            coach_has_access = True
            athlete_has_access = top_category.id == 10001

            if self.recipient.user_type != self.requester.user_type:

                # Create coach->athlete assessment permissions
                if coach and athlete:
                    self._set_category_perm(assessed=athlete.get_assessed(),
                                            assessor=coach.get_assessor(),
                                            assessment_top_category=top_category,
                                            assessor_has_access=coach_has_access)

                    # Create athlete->coach assessment permissions
                    self._set_category_perm(assessed=coach.get_assessed(),
                                            assessor=athlete.get_assessor(),
                                            assessment_top_category=top_category,
                                            assessor_has_access=athlete_has_access)

                if self.invite.team and self.invite.team.owner.user_type != USER_TYPE_ORG:
                    # We grant team owner coach on new athlete
                    if self.recipient.user_type == USER_TYPE_ATHLETE:
                        self._set_category_perm(assessed=athlete.get_assessed(),
                                                assessor=self.invite.team.owner.get_assessor(),
                                                assessment_top_category=top_category,
                                                assessor_has_access=coach_has_access)

                        # We grant new athlete on team owner coach
                        self._set_category_perm(assessed=self.invite.team.owner.get_assessed(),
                                                assessor=athlete.get_assessor(),
                                                assessment_top_category=top_category,
                                                assessor_has_access=athlete_has_access)

                        # We grant all the other coaches of the team on new athlete
                        for other_coach_member in self.invite.team.coaches.all():
                            self._set_category_perm(assessed=athlete.get_assessed(),
                                                    assessor=other_coach_member.get_assessor(),
                                                    assessment_top_category=top_category,
                                                    assessor_has_access=coach_has_access)

                            # We grant new athlete on all the other coaches of the team
                            self._set_category_perm(assessed=other_coach_member.get_assessed(),
                                                    assessor=athlete.get_assessor(),
                                                    assessment_top_category=top_category,
                                                    assessor_has_access=athlete_has_access)

            if self.invite.team \
                    and self.recipient.user_type == USER_TYPE_COACH \
                    and self.invite.team.owner.user_type != USER_TYPE_ORG:

                # Grant new coach permission to asses the owner of the team
                self._set_category_perm(assessed=self.invite.team.owner.get_assessed(),
                                        assessor=self.recipient.coachuser.get_assessor(),
                                        assessment_top_category=top_category,
                                        assessor_has_access=coach_has_access)

                # Grant owner of the team permission to asses a new coach
                self._set_category_perm(assessed=self.recipient.coachuser.get_assessed(),
                                        assessor=self.invite.team.owner.get_assessor(),
                                        assessment_top_category=top_category,
                                        assessor_has_access=athlete_has_access)

                for athlete in self.invite.team.athletes.all():
                    # Grant new coach permission to assess athletes
                    self._set_category_perm(assessed=athlete.get_assessed(),
                                            assessor=self.recipient.coachuser.get_assessor(),
                                            assessment_top_category=top_category,
                                            assessor_has_access=coach_has_access)

                    # Grant athletes permission to assess new coach
                    self._set_category_perm(assessed=self.recipient.coachuser.get_assessed(),
                                            assessor=athlete.get_assessor(),
                                            assessment_top_category=top_category,
                                            assessor_has_access=athlete_has_access)

            if self.invite.team:
                self._grant_team_coach_athlete_perms(top_category, coach_has_access, athlete_has_access)

        return {'requester_first_name': self.requester.first_name,
                'requester_last_name': self.requester.last_name,
                'requester_id': self.requester.id,
                'requester_type': self.requester.user_type}

    def _set_category_perm(self, assessed, assessor, assessment_top_category, assessor_has_access):
        AssessmentTopCategoryPermission.objects.using(self.localized_db).get_or_create(
            assessed=assessed,
            assessor=assessor,
            assessment_top_category=assessment_top_category,
            defaults={
              'assessor_has_access': assessor_has_access,
            },
        )

    def _grant_team_coach_athlete_perms(self, top_category, coach_has_access, athlete_has_access):
        if self.recipient.user_type == USER_TYPE_COACH:
            # New user is COACH
            for athlete in self.invite.team.athletes.all():
                # Grant new coach permission to assess athletes
                self._set_category_perm(assessed=athlete.get_assessed(),
                                        assessor=self.recipient.coachuser.get_assessor(),
                                        assessment_top_category=top_category,
                                        assessor_has_access=coach_has_access)

                # Grant athletes permission to assess new coach
                self._set_category_perm(assessed=self.recipient.coachuser.get_assessed(),
                                        assessor=athlete.get_assessor(),
                                        assessment_top_category=top_category,
                                        assessor_has_access=athlete_has_access)

                Coaching.objects.using(self.localized_db).get_or_create(athlete=athlete, coach=self.recipient.coachuser)
        else:
            # New user is ATHLETE
            for coach in self.invite.team.coaches.all():
                # We grant all the other coaches of the team on new athlete
                self._set_category_perm(assessed=self.recipient.get_assessed(),
                                        assessor=coach.get_assessor(),
                                        assessment_top_category=top_category,
                                        assessor_has_access=coach_has_access)

                # We grant new athlete on all the other coaches of the team
                self._set_category_perm(assessed=coach.get_assessed(),
                                        assessor=self.recipient.get_assessor(),
                                        assessment_top_category=top_category,
                                        assessor_has_access=athlete_has_access)

                Coaching.create_if_not_exist(self.localized_db, self.recipient.athleteuser, coach)


class UserInviteUnlinkSerializer(serializers.Serializer):
    """
    Serializer to unlink connected user by specifying `linked_user` (user email).
    """
    linked_user = serializers.EmailField()

    def validate(self, data):
        self.user = self.context['user']
        self.localized_db = self.user.country

        try:
            linked_user = UserModel.objects.using(self.localized_db).get(email=data.get('linked_user'))
        except UserModel.DoesNotExist:
            raise serializers.ValidationError({"linked_user": _("Unknown user: {}".format(data.get('linked_user')))})

        if linked_user.id == self.user.id:
            raise serializers.ValidationError({"error": _("You can not unlink yourself!")})

        if linked_user.user_type == USER_TYPE_ATHLETE:
            self.athlete = linked_user.athleteuser
            self.coach = self.user.coachuser
        if linked_user.user_type == USER_TYPE_COACH:
            self.athlete = self.user.athleteuser
            self.coach = linked_user.coachuser

        self.coachings = Coaching.objects.using(self.localized_db).filter(athlete=self.athlete, coach=self.coach)

        return data

    def save(self):
        # delete coach-athlete connection if exists
        if self.coachings:
            self.coachings.delete()

        # Cancel existing non-expired pending invites between the two
        Invite.objects.pending_nonexpired().using(self.localized_db) \
            .filter(
            Q(requester=self.athlete.user, recipient=self.coach.user.email) |
            Q(requester=self.coach.user, recipient=self.athlete.user.email)
        ).update(status=INVITE_CANCELED)

        # delete coach-athlete permissions
        AssessmentTopCategoryPermission.objects.using(self.localized_db). \
            filter(assessed_id=self.athlete.user.id, assessor_id=self.coach.user.id).delete()
        # delete athlete-coach permissions
        AssessmentTopCategoryPermission.objects.using(self.localized_db). \
            filter(assessed_id=self.coach.user.id, assessor_id=self.athlete.user.id).delete()

        return True


class UserInviteRevokeListSerializer(serializers.ListSerializer):
    """
    List serializer to call child `.save` method for all validated children from the `.invites` list.
    """
    def update(self, instance, validated_data):
        pass

    def save(self):
        [self.child.save(invite=invite) for invite in self.child.invites or []]


class UserInviteRevokeSerializer(ValidateInviteTokenMixin, serializers.Serializer):
    """
    Serializer to cancel specific invitation (token) by specifying either its `id` or `user_invite_token`.
    """
    user_invite_token = serializers.CharField(required=False)
    id = serializers.IntegerField(required=False)

    class Meta:
        list_serializer_class = UserInviteRevokeListSerializer

    def validate_user_invite_token(self, value):
        return super().validate_user_invite_token(value)

    def validate_id(self, value):
        try:
            self.invite = Invite.objects.using(self.context['user'].country).get(pk=value)

            # Keep track of validated invites in order to have access to them from the parent ListSerializer
            self.invites = self.invites or []
            self.invites.append(self.invite)

            return super().validate(value)

        except Invite.DoesNotExist:
            raise serializers.ValidationError({"id": "Unknown invite id."})

    def validate(self, attrs):
        token = attrs.get('user_invite_token')
        id = attrs.get('id')

        if (not token and not id) or (token and id):
            raise serializers.ValidationError(
                {"error": "Only one of either id or user_invite_token must be specified."})

        return super().validate(attrs)

    def save(self, invite=None):
        if invite is None:
            invite = self.invite

        # Cancel the invite
        invite.status = INVITE_CANCELED
        invite.save(update_fields=('status',))

        return True

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class UserPendingInviteListSerializer(serializers.ModelSerializer):
    """
    Serializer for user's pending invites (sent to him or created by him).
    """
    recipient_name = serializers.SerializerMethodField()

    def get_recipient_name(self, obj):
        return obj.get_recipient_full_name(self.context['request'].user.country)

    class Meta:
        model = Invite
        fields = ('id', 'requester_id', 'recipient', 'team_id', 'date_sent', 'recipient_name')
