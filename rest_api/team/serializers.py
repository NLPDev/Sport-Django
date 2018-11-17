from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from multidb_account.precompetition.models import PreCompetition
from multidb_account.user.models import AthleteUser, BaseCustomUser, Organisation
from multidb_account.team.models import Team
from multidb_account.sport.models import Sport
from multidb_account.constants import USER_TYPE_COACH, USER_TYPE_ATHLETE, USER_TYPE_ORG
from multidb_account.choices import TEAM_STATUSES
from rest_api.precompetition.serializers import PreCompetitionCreateUpdateListSerializer

UserModel = get_user_model()


class AthleteCoachTeamMembersSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.user.id

    def get_email(self, obj):
        return obj.user.email

    def get_first_name(self, obj):
        return obj.user.first_name

    def get_last_name(self, obj):
        return obj.user.last_name

    def get_user_type(self, obj):
        return obj.user.user_type

    def get_status(self, obj):
        if not obj.user.is_athlete():
            return
        status = obj.user.athleteuser.precompetition_set.using(obj.user.country).order_by('-date_created').first()
        if status:
            ser = PreCompetitionCreateUpdateListSerializer(status)
            return {
                k: v for k, v in ser.data.items()
                if k in ('hydration', 'weekly_load', 'injury', 'fatigue', 'stress')
            }

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.user.profile_picture and obj.user.profile_picture.url and request:
            return request.build_absolute_uri(obj.user.profile_picture.url)
        return ''


class TeamSerializer(serializers.ModelSerializer):
    team_id = serializers.IntegerField(required=True)

    class Meta:
        model = Team
        fields = ['team_id']

    def validate_team_id(self, team_id):
        try:
            Team.objects.using(self.context['request'].user.country).get(id=team_id)
        except Team.DoesNotExist:
            raise serializers.ValidationError({"team_id": _("Unknown team: {}".format(team_id))})


class TeamListSerializer(serializers.ModelSerializer):
    """
    Serializer to list a team.
    """
    athletes = AthleteCoachTeamMembersSerializer(many=True, read_only=True)
    coaches = serializers.SerializerMethodField()
    team_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ('id', 'name', 'status', 'season', 'team_picture_url', 'tagline', 'location', 'owner_id', 'sport_id',
                  'athletes', 'coaches')

    def get_coaches(self, obj):
        return AthleteCoachTeamMembersSerializer(
            obj.get_all_coaches(), many=True, context=self.context).data

    def get_team_picture_url(self, obj):
        request = self.context.get('request')
        if obj.team_picture and obj.team_picture.url and request:
            return request.build_absolute_uri(obj.team_picture.url)
        return ''


class TeamCreateSerializer(serializers.ModelSerializer):
    """
    Serializer to list a team.
    """
    sport_id = serializers.IntegerField(required=True)
    status = serializers.ChoiceField(choices=TEAM_STATUSES, required=True)
    location = serializers.CharField(max_length=255, required=True)
    season = serializers.CharField(max_length=25, required=True)

    tagline = serializers.CharField(max_length=500, required=False, allow_blank=True)

    owner_id = serializers.IntegerField(read_only=True)
    athletes = AthleteCoachTeamMembersSerializer(many=True, read_only=True)
    coaches = AthleteCoachTeamMembersSerializer(many=True, read_only=True)
    team_picture_url = serializers.SerializerMethodField()

    is_private = serializers.BooleanField(required=False)
    organisation_id = serializers.IntegerField(required=False)

    class Meta:
        model = Team
        fields = ('id', 'name', 'status', 'season', 'team_picture_url', 'tagline', 'location', 'owner_id', 'sport_id',
                  'athletes', 'coaches', 'is_private', 'organisation_id')

    def get_team_picture_url(self, obj):
        request = self.context.get('request')
        if obj.team_picture and obj.team_picture.url and request:
            return request.build_absolute_uri(obj.team_picture.url)
        return ''

    def create(self, validated_data):
        user = self.context['user']
        validated_data['owner_id'] = user.id
        if user.is_organisation():
            validated_data['organisation_id'] = user.organisation.id
        obj = self.Meta.model.objects.db_manager(self.context.get('country')).create(**validated_data)
        if user.is_coach():
            obj.coaches.add(user.coachuser)
        return obj

    def validate(self, data):
        localized_db = self.context.get('country')
        owner = self.context['user']
        sport_id = data.get('sport_id')
        org_id = data.get('organisation_id')

        if owner.user_type != USER_TYPE_COACH and owner.user_type != USER_TYPE_ORG:
            raise serializers.ValidationError({"owner_id": _("Team's owner should be a coach or an organisation")})

        try:
            Sport.objects.using(localized_db).get(pk=sport_id)
        except Sport.DoesNotExist:
            raise serializers.ValidationError({"sport_id": "Unknown sport_id: %s" % sport_id})

        if org_id:
            try:
                Organisation.objects.using(localized_db).get(pk=org_id)
            except Organisation.DoesNotExist:
                raise serializers.ValidationError({"organisation_id": "Unknown organisation_id: %s" % org_id})

        return data


class TeamUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer to update a team.
    """
    sport_id = serializers.IntegerField(read_only=True)
    owner_id = serializers.IntegerField(read_only=True)

    athletes = AthleteCoachTeamMembersSerializer(many=True, read_only=True)
    coaches = AthleteCoachTeamMembersSerializer(many=True, read_only=True)
    team_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ('id', 'name', 'status', 'season', 'team_picture_url', 'tagline', 'location', 'owner_id', 'sport_id',
                  'athletes', 'coaches')

    def get_team_picture_url(self, obj):
        request = self.context.get('request')
        if obj.team_picture and obj.team_picture.url and request:
            return request.build_absolute_uri(obj.team_picture.url)
        return ''

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.status = validated_data.get('status', instance.status)
        instance.season = validated_data.get('season', instance.season)
        instance.tagline = validated_data.get('tagline', instance.tagline)
        instance.location = validated_data.get('location', instance.location)
        instance.save()
        return instance


class TeamPictureUploadSerializer(serializers.ModelSerializer):
    """
    Serializer to upload/update team's picture.
    """
    team_picture = serializers.ImageField(required=True, write_only=True)
    team_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ('team_picture', 'team_picture_url')

    def get_team_picture_url(self, obj):
        request = self.context.get('request')
        if obj.team_picture and obj.team_picture.url and request:
            return request.build_absolute_uri(obj.team_picture.url)
        return ''


class TeamMembershipOwnershipListSerializer(serializers.ModelSerializer):
    """
    Serializer to list a team membership.
    """
    team_picture_url = serializers.SerializerMethodField()
    sport = serializers.ReadOnlyField(source='sport.description')
    sport_id = serializers.ReadOnlyField(source='sport.id')
    is_private = serializers.ReadOnlyField()
    organisation_id = serializers.ReadOnlyField()

    class Meta:
        model = Team
        fields = ('id', 'name', 'tagline', 'season', 'sport', 'sport_id', 'team_picture_url', 'is_private',
                  'organisation_id')

    def get_team_picture_url(self, obj):
        request = self.context.get('request')
        if obj.team_picture and obj.team_picture.url and request:
            return request.build_absolute_uri(obj.team_picture.url)
        return ''


class TeamRevokeSerializer(serializers.Serializer):
    """
    Serializer to revoke team members.
    """

    team_id = serializers.IntegerField(required=True)
    user_id = serializers.IntegerField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = self.context['user']
        self.localized_db = self.user.country
        self.team = self.team_members = self.revokee = None

    def validate(self, data):

        # Fetch team obj
        team_id = data.get('team_id')
        try:
            self.team = Team.objects.using(self.localized_db).get(id=team_id)
        except Team.DoesNotExist:
            raise serializers.ValidationError({"team_id": _("Unknown team: {}".format(team_id))})

        # Fetch revokee user obj
        revokee_id = data.get('user_id')
        try:
            revokee_base = BaseCustomUser.objects.using(self.localized_db).get(id=revokee_id)
        except BaseCustomUser.DoesNotExist:
            raise serializers.ValidationError({"user_id": _("Unknown user: {}".format(revokee_id))})

        # Check ownership
        if revokee_id != self.user.id and self.user != self.team.owner:
            raise serializers.ValidationError({"error": _("You are not the owner of the team.")})

        # Detect team members collection
        if revokee_base.user_type == USER_TYPE_ATHLETE:
            self.revokee = revokee_base.athleteuser
            self.team_members = self.team.athletes
        else:
            self.revokee = revokee_base.coachuser
            self.team_members = self.team.coaches

        if self.revokee not in self.team_members.all():
            raise serializers.ValidationError({"error": _("User with this id doesn't belong to this team.")})

        return data

    def save(self):
        self.team_members.remove(self.revokee)
        return True

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class AthleteListSerializer(serializers.ModelSerializer):
    """
    Assessed Serializer.
    """
    id = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.user_id

    def get_first_name(self, obj):
        return obj.user.first_name

    def get_last_name(self, obj):
        return obj.user.last_name

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.user.profile_picture and obj.user.profile_picture.url and request:
            return request.build_absolute_uri(obj.user.profile_picture.url)
        return ''

    class Meta:
        model = AthleteUser
        fields = ('id', 'first_name', 'last_name', 'profile_picture_url')


class TeamPreCompetitionListSerializer(serializers.ModelSerializer):
    """
    Serializer to list a team.
    """
    athlete = AthleteListSerializer(read_only=True)

    class Meta:
        model = PreCompetition
        fields = ('id', 'title', 'goal', 'athlete', 'team_id', 'date', 'stress', 'fatigue', 'hydration',
                  'injury', 'weekly_load')

