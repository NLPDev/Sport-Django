from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from multidb_account.note.models import File, AthleteNote, ReturnToPlayType, Link, CoachNote
from multidb_account.team.models import Team
from multidb_account.user.models import AthleteUser, CoachUser

UserModel = get_user_model()


class FileSerializer(serializers.ModelSerializer):
    """
    File serializer.
    """

    owner = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    file = serializers.FileField(required=False, write_only=True)

    class Meta:
        model = File
        read_only_fields = ('id', 'owner', 'date_created')
        fields = read_only_fields + ('file',)

    def create(self, validated_data):
        return self.Meta.model.objects.db_manager(validated_data['owner'].country).create(**validated_data)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data['file'] = obj.file.url
        return data


from urllib.parse import urlparse
from django.core.exceptions import ValidationError


def validate_url(value):
    parsed = urlparse(value)
    if parsed.scheme not in ['https', 'http'] and not parsed.path.startswith('www'):
        raise ValidationError(
            _('%(value)s is not a valid url'),
            params={'value': value},
        )


class AthleteNoteSerializer(serializers.ModelSerializer):
    """
    AthleteNote serializer.
    """

    owner = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    files = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True, allow_null=True)
    links = serializers.ListField(child=serializers.CharField(validators=[
        RegexValidator(regex=r'(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)?[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?'),
        validate_url

    ]), required=False, write_only=True, allow_null=True)
    return_to_play_type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    only_visible_to = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = AthleteNote
        read_only_fields = ('id', 'owner', 'date_created', 'owner_name')
        fields = read_only_fields + ('title', 'return_to_play_type', 'note', 'links', 'files', 'only_visible_to')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.country = self.context['request'].user.country

    def validate_return_to_play_type(self, value):
        if not value:
            return

        try:
            return ReturnToPlayType.objects.using(self.country).get(pk=value)
        except ReturnToPlayType.DoesNotExist:
            raise serializers.ValidationError(
                {"return_to_play_type": _("Unknown return_to_play_type: {}".format(value))})

    # noinspection PyMethodMayBeStatic
    def validate_owner(self, value):
        try:
            return value.athleteuser
        except ObjectDoesNotExist:
            raise serializers.ValidationError({"error": _("You are not an athlete.")})

    def validate_files(self, value):
        if value is None:
            return
        files = []

        for file_id in value:
            try:
                files.append(File.objects.using(self.country).get(pk=file_id))
            except File.DoesNotExist:
                raise serializers.ValidationError({"files": _("Unknown file with id: {}".format(file_id))})

        return files

    def validate_only_visible_to(self, value):
        users = []

        for user_id in value:
            try:
                users.append(CoachUser.objects.using(self.country).get(pk=user_id))
            except CoachUser.DoesNotExist:
                raise serializers.ValidationError({"only_visible_to": _("Unknown coach with id: {}".format(user_id))})

        return users

    def validate_links(self, value):
        if value is None:
            return
        links = []

        for url in value:
            link, _ = Link.objects.using(self.country).get_or_create(url=url)
            links.append(link)

        return links

    def create(self, validated_data):
        files = validated_data.pop('files', [])
        links = validated_data.pop('links', [])
        only_visible_to = validated_data.pop('only_visible_to', [])

        obj = self.Meta.model.objects.db_manager(self.country).create(**validated_data)
        obj.files.db_manager(self.country).set(files)
        obj.links.db_manager(self.country).set(links)
        obj.only_visible_to.db_manager(self.country).set(only_visible_to)

        return obj

    def to_representation(self, obj):
        data = super().to_representation(obj)

        data['files'] = FileSerializer(obj.files.using(self.country).all(), many=True).data
        data['only_visible_to'] = [user.user.id for user in obj.only_visible_to.using(self.country).all()]
        data['links'] = [link.url for link in obj.links.using(self.country).all()]

        return data


class CoachNoteSerializer(serializers.ModelSerializer):
    """
    CoachNote serializer.
    """

    owner = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    files = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True, allow_null=True)
    links = serializers.ListField(child=serializers.CharField(validators=[
        RegexValidator(regex=r'(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)?[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?'),
        validate_url

    ]), required=False, write_only=True, allow_null=True)
    team_id = serializers.IntegerField(required=False, allow_null=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    athlete_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = CoachNote
        read_only_fields = ('id', 'owner', 'date_created', 'team_name', 'owner_name')
        fields = read_only_fields + ('title', 'note', 'links', 'files', 'team_id', 'athlete_id')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.country = self.context['request'].user.country

    def validate_athlete_id(self, value):
        if value is None:
            return

        try:
            return AthleteUser.objects.using(self.country).get(pk=value).user.id
        except AthleteUser.DoesNotExist:
            raise serializers.ValidationError({"athlete_id": _("Unknown athlete_id: {}".format(value))})

    # noinspection PyMethodMayBeStatic
    def validate_team_id(self, value):
        if value is None:
            return

        try:
            return Team.objects.using(self.country).get(pk=value).id
        except Team.DoesNotExist:
            raise serializers.ValidationError({"team_id": _("Unknown team_id: {}".format(value))})

    # noinspection PyMethodMayBeStatic
    def validate_owner(self, value):
        try:
            return value.coachuser
        except ObjectDoesNotExist:
            raise serializers.ValidationError({"error": _("You are not a coach.")})

    def validate_files(self, value):
        if value is None:
            return
        files = []

        for file_id in value:
            try:
                files.append(File.objects.using(self.country).get(pk=file_id))
            except File.DoesNotExist:
                raise serializers.ValidationError({"files": _("Unknown file with id: {}".format(file_id))})

        return files

    def validate_links(self, value):
        if value is None:
            return
        links = []

        for url in value:
            link, _ = Link.objects.using(self.country).get_or_create(url=url)
            links.append(link)

        return links

    def validate(self, attrs):
        if attrs.get('team_id') is not None and attrs.get('athlete_id') is not None:
            raise serializers.ValidationError({"error": _("Either athlete_id or team_id should be specified.")})

        return super().validate(attrs)

    def create(self, validated_data):
        files = validated_data.pop('files', [])
        links = validated_data.pop('links', [])

        obj = self.Meta.model.objects.db_manager(self.country).create(**validated_data)
        obj.files.db_manager(self.country).set(files)
        obj.links.db_manager(self.country).set(links)

        return obj

    def to_representation(self, obj):
        data = super().to_representation(obj)

        data['files'] = FileSerializer(obj.files.using(self.country).all(), many=True).data
        data['links'] = [link.url for link in obj.links.using(self.country).all()]

        return data


class ReturnToPlayTypeSerializer(serializers.ModelSerializer):
    """
    ReturnToPlayType serializer.
    """
    class Meta:
        model = ReturnToPlayType
        read_only_fields = ('value',)
        fields = read_only_fields
