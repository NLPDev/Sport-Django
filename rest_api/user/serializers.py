from collections import defaultdict
from itertools import chain

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db.models import Q
from rest_framework import serializers

from multidb_account.assessment.models import AssessmentTopCategory, Assessed, AssessmentTopCategoryPermission, Assessor
from multidb_account.choices import MEASURING, USER_TYPES
from multidb_account.constants import USER_TYPE_COACH, USER_TYPE_ATHLETE, USER_TYPE_ORG
from multidb_account.sport.models import Sport, ChosenSport
from multidb_account.user.models import AthleteUser, CoachUser, Organisation, Coaching
from multidb_account.utils import get_user_from_localized_databases
from payment_gateway.models import Customer
from rest_api.assessment.serializers import AssessmentTopCategorySerializer
from rest_api.education.serializers import EducationSerializer
from rest_api.team.serializers import TeamMembershipOwnershipListSerializer
from rest_api.utils import generate_user_jwt_token

UserModel = get_user_model()


class CustomUserRegistrationChosenSport(serializers.ModelSerializer):
    """
    Serializer for user's chosen sports.
    """
    sport_id = serializers.IntegerField(required=True)
    sport = serializers.CharField(required=False)
    is_displayed = serializers.BooleanField(required=True)
    is_chosen = serializers.BooleanField(required=True)

    class Meta:
        model = ChosenSport
        fields = ('sport_id', 'sport', 'is_displayed', 'is_chosen')


class CustomUserListChosenSport(serializers.ModelSerializer):
    """
    Serializer for user's chosen sports.
    """
    sport_id = serializers.ReadOnlyField(source='sport.id')
    sport = serializers.ReadOnlyField(source='sport.description')
    is_displayed = serializers.BooleanField()
    is_chosen = serializers.BooleanField()

    class Meta:
        model = ChosenSport
        fields = ('sport_id', 'sport', 'is_displayed', 'is_chosen')


class GrantedChosenSport(serializers.ModelSerializer):
    """
    Serializer for user's chosen sports.
    """
    sport_id = serializers.ReadOnlyField(source='sport.id')
    sport = serializers.ReadOnlyField(source='sport.description')

    class Meta:
        model = ChosenSport
        fields = ('sport_id', 'sport')


class ResetPasswordSerializer(serializers.ModelSerializer):
    """
    Serializer for forgot password request endpoint.
    """
    email = serializers.EmailField(required=True)

    class Meta:
        model = UserModel
        fields = ('email',)

    def validate(self, data):
        if not get_user_from_localized_databases(data.get('email')):
            raise serializers.ValidationError({"email": "Unknown email address: {}".format(data.get('email'))})
        return data


class ResetPasswordConfirmSerializer(serializers.ModelSerializer):
    """
    Serializer for reset password confirmation endpoint.
    """
    # only used for reset(write)
    password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)
    reset_password_token = serializers.CharField(required=True, write_only=True)

    # Read-only field: JWT token returned after registration
    token = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = ('password', 'confirm_password', 'reset_password_token', 'token')
        extra_kwargs = {
            'token': {},
        }

    def get_token(self, obj):
        token = generate_user_jwt_token(self.user)
        return token

    def validate_reset_password_token(self, value):
        try:
            email = signing.loads(value, max_age=getattr(django_settings, 'PASSWORD_RESET_TOKEN_EXPIRES'),
                                  salt=self.context['salt'])
        except signing.BadSignature:
            raise serializers.ValidationError("Reset password token is not valid.")

        if email:
            user = get_user_from_localized_databases(email)
            if user:
                self.user = user
                return value
            else:
                raise serializers.ValidationError("Reset password token is not valid.")
        else:
            raise serializers.ValidationError("Reset password token is not valid.")

    def validate(self, data):
        if not data.get('reset_password_token'):
            raise serializers.ValidationError("Please provide a reset password token.")

        if not data.get('password') or not data.get('confirm_password'):
            raise serializers.ValidationError("Please enter a password and confirmation password.")

        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError("Passwords don't match.")

        return data

    def save(self):
        self.user.set_password(self.validated_data.get('password'))
        self.user.save(using=self.user.country)
        return self.user


class ChangePasswordSerializer(serializers.ModelSerializer):
    """
    Serializer for password change endpoint.
    """
    password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)
    current_password = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = UserModel
        fields = ('password', 'confirm_password', 'current_password')

    def validate(self, data):
        self.user = self.context['user']

        if not data.get('current_password'):
            raise serializers.ValidationError({"current_password": "Please enter the current password."})

        if not self.user.check_password(data.get('current_password')):
            raise serializers.ValidationError({"current_password": "Please enter the current correct password."})

        if not data.get('password') or not data.get('confirm_password'):
            raise serializers.ValidationError(
                {"confirm_password": "Please enter a password and confirmation password."})

        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"password": "New passwords don't match."})

        if data.get('password') == data.get('current_password'):
            raise serializers.ValidationError({"password": "The new password has to be different."})

        return data

    def save(self):
        self.user.set_password(self.validated_data.get('password'))
        self.user.save(using=self.user.country)
        # TODO: Add autologout
        return self.user


class UserAllTeamsSerializer(serializers.Serializer):
    is_coaching = serializers.BooleanField()
    team_name = serializers.CharField()
    team_id = serializers.IntegerField()


class AthleteCoachLinkedSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    granted_assessment_top_categories = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()
    teams = serializers.SerializerMethodField()
    all_teams = serializers.SerializerMethodField()
    chosen_sports = serializers.SerializerMethodField()

    def _get_user(self, obj):
        return obj.user if hasattr(obj, 'user') else obj

    def get_id(self, obj):
        return self._get_user(obj).pk

    def get_email(self, obj):
        return self._get_user(obj).email

    def get_first_name(self, obj):
        return self._get_user(obj).first_name

    def get_last_name(self, obj):
        return self._get_user(obj).last_name

    def get_user_type(self, obj):
        return self._get_user(obj).user_type

    def get_chosen_sports(self, obj):
        ser = CustomUserRegistrationChosenSport(data=self._get_user(obj).chosensport_set.all(), many=True)
        ser.is_valid()
        return ser.data

    def get_tagline(self, obj):
        return self._get_user(obj).tagline

    def get_teams(self, obj):
        coach_teams = self.context.get('coach_teams', {})
        teams = coach_teams.get(obj.pk, [])
        return [x.name for x in teams]

    def get_all_teams(self, obj):
        qs = []
        is_coaching = None
        only_org_teams = Q(organisation__isnull=False)

        if hasattr(obj, 'athleteuser'):
            is_coaching = False
            qs = obj.athleteuser.team_membership.filter(only_org_teams)
        elif hasattr(obj, 'coachuser'):
            is_coaching = True
            qs = obj.coachuser.team_membership.filter(only_org_teams)

        data = [{
            'is_coaching': is_coaching,
            'team_id': t.id,
            'team_name': t.name,
        } for t in qs]

        ser = UserAllTeamsSerializer(many=True, data=data)
        ser.is_valid()
        return ser.data

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        user = self._get_user(obj)
        if user.profile_picture and user.profile_picture.url and request:
            return request.build_absolute_uri(user.profile_picture.url)
        return ''

    def get_granted_assessment_top_categories(self, obj):
        request = self.context.get('request')
        request_user = request.user
        obj_user = self._get_user(obj)
        # we list sports chosen + displayed + granted to coach by the athlete (athlete=obj here)
        if obj_user.user_type == USER_TYPE_ATHLETE:
            assessed_from_org_team = Q(assessed__athlete__team_membership__organisation__login_users=request_user) | \
                                     Q(assessed__coach__team_membership__organisation__login_users=request_user)

            granted_assessment_top_category_ids = AssessmentTopCategoryPermission.objects.using(request.user.country) \
                .filter(Q(assessor_id=request_user.id) | assessed_from_org_team,
                        assessed_id=obj_user.pk,
                        assessor_has_access=True) \
                .values_list('assessment_top_category__id', flat=True)

            granted_assessment_top_categories = AssessmentTopCategory.objects.using(request.user.country) \
                .filter(pk__in=granted_assessment_top_category_ids)

            return AssessmentTopCategorySerializer(granted_assessment_top_categories, many=True).data
        return []


class CustomUserLoginSerializer(serializers.Serializer):
    """
    Serializer for login endpoint.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    token = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = ('id', 'email', 'password', 'token',)

    def get_token(self, obj):
        token = generate_user_jwt_token(self.user)
        return token

    def get_id(self, obj):
        return self.user.id

    def validate(self, data):
        self.user = get_user_from_localized_databases(data.get('email'))

        if not self.user:
            raise serializers.ValidationError({"email": "Unknown email address: {}".format(data.get('email'))})

        if not self.user.check_password(data.get('password')):
            raise serializers.ValidationError({"password": "Unable to login. Incorrect password."})

        return data


class CustomUserProfilePictureUploadSerializer(serializers.ModelSerializer):
    """
    Serializer to upload/update user's profile picture.
    """
    profile_picture = serializers.ImageField(required=True, write_only=True)
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = ('profile_picture', 'profile_picture_url')

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and obj.profile_picture.url and request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return ''


class CustomUserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration endpoint.
    """
    # Required fields by model design: email, country, password
    # user_type required for registration
    user_type = serializers.ChoiceField(choices=USER_TYPES, required=True)
    first_name = serializers.CharField(required=True, allow_blank=False)
    last_name = serializers.CharField(required=True, allow_blank=False)

    # only used for registration(write)
    password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    # Optional fields
    province_or_state = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False)
    newsletter = serializers.BooleanField(required=False)
    terms_conditions = serializers.BooleanField(required=False)
    tagline = serializers.CharField(max_length=500, required=False, allow_blank=True)
    measuring_system = serializers.ChoiceField(choices=MEASURING, required=False)

    # Write-only fields
    profile_picture_url = serializers.SerializerMethodField()
    profile_complete = serializers.BooleanField(read_only=True)

    # Nested field (intermediate table)
    chosen_sports = CustomUserRegistrationChosenSport(source='chosensport_set', many=True, required=False)
    linked_users = serializers.SerializerMethodField()

    team_memberships = serializers.SerializerMethodField()

    # Read-only field: JWT token returned after registration
    token = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = ('id', 'email', 'country', 'province_or_state', 'city', 'password', 'confirm_password', 'user_type',
                  'first_name', 'last_name', 'date_of_birth', 'newsletter', 'terms_conditions', 'tagline',
                  'chosen_sports', 'profile_complete', 'measuring_system', 'profile_picture_url',
                  'token', 'linked_users', 'team_memberships')

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and obj.profile_picture.url and request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return ''

    def get_linked_users(self, obj):
        request = self.context.get('request')

        linked_users = obj.get_linked_users() if request else []

        return AthleteCoachLinkedSerializer(linked_users, many=True,
                                            context={"request": request}).data

    def get_team_memberships(self, obj):
        request = self.context.get('request')
        teams = []
        if obj.user_type == USER_TYPE_ATHLETE and request:
            teams = obj.athleteuser.team_membership.all()
        if obj.user_type == USER_TYPE_COACH and request:
            teams = obj.coachuser.team_membership.all()
        return TeamMembershipOwnershipListSerializer(teams, many=True, context={"request": request}).data

    def get_token(self, obj):
        user = obj
        token = generate_user_jwt_token(user)
        return token

    def create(self, validated_data):
        required_data = {}
        required_data.update({'email': validated_data.get('email')})
        required_data.update({'country': validated_data.get('country')})
        required_data.update({'password': validated_data.get('password')})
        if 'is_active' in validated_data:
            required_data['is_active'] = validated_data['is_active']

        user = UserModel.objects.create_user(**required_data)
        user.user_type = validated_data.get('user_type', '')
        user.province_or_state = validated_data.get('province_or_state', '')
        user.city = validated_data.get('city', '')
        user.first_name = validated_data.get('first_name', '')
        user.last_name = validated_data.get('last_name', '')
        user.date_of_birth = validated_data.get('date_of_birth')
        user.newsletter = validated_data.get('newsletter', False)
        user.terms_conditions = validated_data.get('terms_conditions', False)
        user.tagline = validated_data.get('tagline', '')
        user.measuring_system = validated_data.get('measuring_system', 'metric')

        # create default user's chosen sport and set value if if specified in the validated_data
        for default_sport in Sport.objects.using(user.country).filter(is_available=True):
            ChosenSport.objects.using(user.country).create(user_id=user.id, sport_id=default_sport.id,
                                                           is_chosen=False, is_displayed=False)

        if validated_data.get('chosensport_set'):
            for sport_data in validated_data.get('chosensport_set'):
                chosen_sport = ChosenSport.objects.using(user.country).get(user_id=user.id,
                                                                           sport_id=sport_data.get('sport_id'))
                chosen_sport.is_chosen = sport_data.get('is_chosen', chosen_sport.is_chosen)
                chosen_sport.is_displayed = sport_data.get('is_displayed', chosen_sport.is_displayed)
                chosen_sport.save(using=user.country)

        # Add the user model extensions based on the user_type
        if validated_data.get('user_type') == USER_TYPE_ATHLETE:
            at = AthleteUser(user=user)
            at.save(using=user.country)
            # Customer extension
            cu = Customer(athlete=at)
            cu.save(using=user.country)
            # Assessed extension
            assed = Assessed(id=at.user_id, athlete=at)
            assed.save(using=user.country)
            # Assessor extension
            assor = Assessor(id=at.user_id, athlete=at)
            assor.save(using=user.country)

        elif validated_data.get('user_type') == USER_TYPE_COACH:
            co = CoachUser(user=user)
            co.save(using=user.country)
            # Assessed extension
            assed = Assessed(id=co.user_id, coach=co)
            assed.save(using=user.country)
            # Assessor extension
            assor = Assessor(id=co.user_id, coach=co)
            assor.save(using=user.country)

        elif validated_data.get('user_type') == USER_TYPE_ORG:
            org_data = validated_data.get('organisation', {})
            org = Organisation(**org_data)
            org.save(using=user.country)
            org.login_users.add(user)

        user.save(using=user.country)
        return user

    def validate(self, data):

        if data['user_type'] != USER_TYPE_ORG:
            if not data.get('password') or not data.get('confirm_password'):
                raise serializers.ValidationError("Please enter a password and confirmation password.")

        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError("Passwords don't match.")

        if get_user_from_localized_databases(data.get('email')):
            raise serializers.ValidationError({"email": "Another user already exists with the same email"})

        if not data.get('country') in getattr(django_settings, 'LOCALIZED_DATABASES', None):
            raise serializers.ValidationError({"country": "Unsupported country code: {}".format(data.get('country'))})

        try:
            if data.get('chosensport_set'):
                for sport_data in data.get('chosensport_set'):
                    Sport.objects.using(data.get('country')).get(pk=sport_data.get('sport_id'))
        except Sport.DoesNotExist:
            raise serializers.ValidationError({"chosen_sports": "Unknown sport_id: {}".
                                              format(sport_data.get('sport_id'))})
        return data


class AthleteUserRegistrationSerializer(CustomUserRegistrationSerializer):
    """
    Serializer for athlete user extension.
    """

    referral_code = serializers.CharField(source='athleteuser.referral_code', required=False, allow_blank=True)
    athlete_terms_conditions = serializers.BooleanField(source='athleteuser.athlete_terms_conditions', required=False)

    class Meta(CustomUserRegistrationSerializer.Meta):
        fields = CustomUserRegistrationSerializer.Meta.fields + ('referral_code', 'athlete_terms_conditions')

    def create(self, validated_data):
        user = super(AthleteUserRegistrationSerializer, self).create(validated_data)
        if validated_data.get('athleteuser') is not None:
            if validated_data.get('athleteuser').get('athlete_terms_conditions') is not None:
                user.athleteuser.athlete_terms_conditions = validated_data.get('athleteuser'). \
                    get('athlete_terms_conditions')
            if validated_data.get('athleteuser').get('referral_code') is not None:
                user.athleteuser.referral_code = validated_data.get('athleteuser').get('referral_code')
        user.athleteuser.save()
        return user


class AthleteUserCustomerRegistrationSerializer(AthleteUserRegistrationSerializer):
    """
    Serializer for athlete user customer extension.
    """
    payment_status = serializers.CharField(source='athleteuser.customer.payment_status', read_only=True)

    class Meta(AthleteUserRegistrationSerializer.Meta):
        fields = AthleteUserRegistrationSerializer.Meta.fields + ('payment_status',)


class CoachUserRegistrationSerializer(CustomUserRegistrationSerializer):
    """
    Serializer to update coach profile.
    """
    team_ownerships = serializers.SerializerMethodField()

    def get_team_ownerships(self, obj):
        request = self.context.get('request')
        teams = []
        if obj.user_type == USER_TYPE_COACH and request:
            teams = obj.team_ownership.all()
        return TeamMembershipOwnershipListSerializer(teams, many=True, context={"request": request}).data

    class Meta(CustomUserRegistrationSerializer.Meta):
        fields = CustomUserRegistrationSerializer.Meta.fields + ('team_ownerships',)


class OrganisationUserRegistrationSerializer(CustomUserRegistrationSerializer):
    """
    Serializer to create organisation profile.
    """
    organisation_name = serializers.CharField(write_only=True)
    size = serializers.IntegerField(write_only=True, required=False)
    description = serializers.CharField(write_only=True, required=False)
    sports = serializers.ListField(write_only=True, required=False)
    phone_number = serializers.CharField(source='basecustomuser.phone_number', required=False)

    # override the base class fields to make them optional
    last_name = serializers.CharField(required=False, allow_blank=False)
    password = serializers.CharField(required=False, write_only=True)
    confirm_password = serializers.CharField(required=False, write_only=True)
    team_ownerships = serializers.SerializerMethodField()

    def get_team_ownerships(self, obj):
        request = self.context.get('request')
        teams = []
        if obj.user_type == USER_TYPE_ORG and request:
            teams = obj.team_ownership.all()
        return TeamMembershipOwnershipListSerializer(teams, many=True, context={"request": request}).data

    def to_internal_value(self, data):
        super_data = super().to_internal_value(data)
        super_data['organisation'] = {
            'name': super_data.pop('organisation_name'),
            'size': super_data.pop('size', None),
            'description': super_data.pop('description', ''),
            'sports': super_data.pop('sports', []),
        }
        return super_data

    def to_representation(self, obj):
        data = super().to_representation(obj)
        org = obj.organisation
        data['organisation_name'] = org.name
        data['size'] = org.size
        data['description'] = org.description
        return data

    class Meta(CustomUserRegistrationSerializer.Meta):
        fields = CustomUserRegistrationSerializer.Meta.fields + \
                 ('size', 'description', 'sports', 'phone_number', 'organisation_name', 'team_ownerships')


class CustomUserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for user update endpoint.
    """
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    # Make fields optional for update as we want to support partial updates
    email = serializers.EmailField(required=False)
    province_or_state = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False)
    newsletter = serializers.BooleanField(required=False)
    terms_conditions = serializers.BooleanField(required=False)
    tagline = serializers.CharField(max_length=500, required=False, allow_blank=True)
    measuring_system = serializers.ChoiceField(choices=MEASURING, required=False)

    # Write-only fields
    profile_picture_url = serializers.SerializerMethodField()

    # Read-only fields
    profile_complete = serializers.BooleanField(read_only=True)
    country = serializers.CharField(read_only=True)
    user_type = serializers.CharField(read_only=True)

    # Nested field (intermediate table)
    chosen_sports = CustomUserRegistrationChosenSport(source='chosensport_set', many=True, required=False)
    schools = EducationSerializer(source='education_set', many=True, required=False)

    linked_users = serializers.SerializerMethodField()

    team_memberships = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = ('id', 'email', 'country', 'province_or_state', 'city', 'user_type', 'first_name', 'last_name',
                  'date_of_birth', 'newsletter', 'terms_conditions', 'tagline', 'chosen_sports', 'profile_complete',
                  'measuring_system', 'profile_picture_url', 'linked_users', 'team_memberships', 'schools',
                  'new_dashboard')

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and obj.profile_picture.url and request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return ''

    def get_linked_users(self, obj):
        request = self.context.get('request')
        linked_users = []
        if obj.user_type == USER_TYPE_ATHLETE and request:
            coaches = []
            # one to one connections
            coaches.extend(list(obj.athleteuser.coaches.all()))
            # connections through teams
            for team in obj.athleteuser.team_membership.all():
                coaches.extend(team.get_all_coaches())
            linked_users = AthleteCoachLinkedSerializer(set(coaches), many=True, context={"request": request}).data

        if obj.user_type == USER_TYPE_COACH and request:
            athletes = []
            # one to one connections
            athletes.extend(list(obj.coachuser.athleteuser_set.all()))
            # connections through teams
            for team in (obj.coachuser.team_membership.all() | obj.team_ownership.all()).distinct():
                athletes.extend(team.get_all_athletes())
            linked_users = AthleteCoachLinkedSerializer(set(athletes), many=True, context={"request": request}).data
        return linked_users

    def get_team_memberships(self, obj):
        request = self.context.get('request')
        teams = []
        if obj.user_type == USER_TYPE_ATHLETE and request:
            teams = obj.athleteuser.team_membership.all()
        if obj.user_type == USER_TYPE_COACH and request:
            teams = obj.coachuser.team_membership.all()
        return TeamMembershipOwnershipListSerializer(teams, many=True, context={"request": request}).data

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.province_or_state = validated_data.get('province_or_state', instance.province_or_state)
        instance.city = validated_data.get('city', instance.city)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.date_of_birth = validated_data.get('date_of_birth', instance.date_of_birth)
        instance.newsletter = validated_data.get('newsletter', instance.newsletter)
        instance.terms_conditions = validated_data.get('terms_conditions', instance.terms_conditions)
        instance.tagline = validated_data.get('tagline', instance.tagline)
        instance.measuring_system = validated_data.get('measuring_system', instance.measuring_system)

        # Update/or create user's chosen_sports if specified in the validated_data
        if validated_data.get('chosensport_set'):
            for sport_data in validated_data.get('chosensport_set'):
                try:
                    chosen_sport = ChosenSport.objects.using(instance.country).get(user_id=instance.id,
                                                                                   sport_id=sport_data.get('sport_id'))
                    chosen_sport.is_chosen = sport_data.get('is_chosen', chosen_sport.is_chosen)
                    chosen_sport.is_displayed = sport_data.get('is_displayed', chosen_sport.is_displayed)
                    chosen_sport.save(using=instance.country)
                except ChosenSport.DoesNotExist:
                    # Create user's chosen_sports if doesn't exist
                    ChosenSport.objects.using(instance.country). \
                        create(user_id=instance.id,
                               sport_id=sport_data.get('sport_id'),
                               is_chosen=sport_data.get('is_chosen', False),
                               is_displayed=sport_data.get('is_displayed', False))
        instance.save()
        return instance

    def validate(self, data):
        try:
            if data.get('chosensport_set'):
                for sport_data in data.get('chosensport_set'):
                    Sport.objects.using(self.instance.country).get(pk=sport_data.get('sport_id'))
        except Sport.DoesNotExist:
            raise serializers.ValidationError({"chosen_sports": "Unknown sport_id: {}".
                                              format(sport_data.get('sport_id'))})

        return data


class AthleteUserUpdateSerializer(CustomUserUpdateSerializer):
    """
    Serializer to update athlete profile.
    """
    promocode = serializers.CharField(source='athleteuser.promocode', required=False, allow_blank=True)
    referral_code = serializers.CharField(source='athleteuser.referral_code', required=False, allow_blank=True)
    athlete_terms_conditions = serializers.BooleanField(source='athleteuser.athlete_terms_conditions', required=False)

    class Meta(CustomUserUpdateSerializer.Meta):
        fields = CustomUserUpdateSerializer.Meta.fields + ('referral_code', 'athlete_terms_conditions', 'promocode')

    def update(self, instance, validated_data):
        instance = super(AthleteUserUpdateSerializer, self).update(instance, validated_data)
        if validated_data.get('athleteuser') is not None:
            if validated_data.get('athleteuser').get('athlete_terms_conditions') is not None:
                instance.athleteuser.athlete_terms_conditions = validated_data.get('athleteuser'). \
                    get('athlete_terms_conditions', instance.athleteuser.athlete_terms_conditions)

            if validated_data.get('athleteuser').get('referral_code') is not None:
                instance.athleteuser.referral_code = validated_data.get('athleteuser'). \
                    get('referral_code', instance.athleteuser.referral_code)

            if validated_data.get('athleteuser').get('promocode') is not None:
                instance.athleteuser.promocode = validated_data.get('athleteuser'). \
                    get('promocode', instance.athleteuser.promocode)

        instance.athleteuser.save()
        return instance


class AthleteUserCustomerUpdateSerializer(AthleteUserUpdateSerializer):
    """
    Serializer for athlete user customer extension.
    """
    payment_status = serializers.CharField(source='athleteuser.customer.payment_status', read_only=True)

    class Meta(AthleteUserUpdateSerializer.Meta):
        fields = AthleteUserUpdateSerializer.Meta.fields + ('payment_status',)


class CoachUserUpdateSerializer(CustomUserUpdateSerializer):
    """
    Serializer to update coach profile.
    """
    team_ownerships = serializers.SerializerMethodField()

    def get_team_ownerships(self, obj):
        request = self.context.get('request')
        teams = []
        if obj.user_type == USER_TYPE_COACH and request:
            teams = obj.team_ownership.all()
        return TeamMembershipOwnershipListSerializer(teams, many=True, context={"request": request}).data

    class Meta(CustomUserUpdateSerializer.Meta):
        fields = CustomUserUpdateSerializer.Meta.fields + ('team_ownerships',)


class OrganisationUserUpdateSerializer(CustomUserUpdateSerializer):
    """
    Serializer to update organisation profile.
    """
    organisation_name = serializers.CharField(write_only=True)
    size = serializers.IntegerField(write_only=True, required=False)
    description = serializers.CharField(write_only=True, required=False)
    sports = serializers.ListField(write_only=True, required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    phone_number = serializers.CharField(source='basecustomuser.phone_number', required=False, allow_blank=True)
    team_ownerships = serializers.SerializerMethodField()

    def get_team_ownerships(self, obj):
        request = self.context.get('request')
        teams = []
        if obj.user_type == USER_TYPE_ORG and request:
            teams = obj.team_ownership.all()
        return TeamMembershipOwnershipListSerializer(teams, many=True, context={"request": request}).data

    def to_internal_value(self, data):
        super_data = super().to_internal_value(data)
        super_data['organisation'] = {
            'name': super_data.pop('organisation_name'),
            'size': super_data.pop('size', None),
            'description': super_data.pop('description', ''),
            'sports': super_data.pop('sports', []),
        }
        return super_data

    class Meta(CustomUserUpdateSerializer.Meta):
        fields = CustomUserUpdateSerializer.Meta.fields + \
                 ('size', 'description', 'sports', 'phone_number', 'organisation_name', 'team_ownerships')


class CustomUserListSerializer(serializers.ModelSerializer):
    """
    Serializer for user list endpoint.
    """
    # Read-only fields
    profile_complete = serializers.BooleanField(read_only=True)
    profile_picture_url = serializers.SerializerMethodField()

    # Nested field (intermediate table)
    chosen_sports = CustomUserListChosenSport(source='chosensport_set', many=True)
    schools = EducationSerializer(source='education_set', many=True)

    linked_users = serializers.SerializerMethodField()
    team_memberships = serializers.SerializerMethodField()
    organisations = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = ('id', 'email', 'country', 'province_or_state', 'city', 'user_type', 'first_name', 'last_name',
                  'date_of_birth', 'newsletter', 'terms_conditions', 'tagline', 'chosen_sports', 'profile_complete',
                  'measuring_system', 'profile_picture_url', 'linked_users', 'team_memberships', 'schools',
                  'new_dashboard', 'organisations')

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and obj.profile_picture.url and request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return ''

    def get_organisations(self, obj):
        ser = OrganisationSerializer(many=True, data=obj.member_of_organisations.all())
        ser.is_valid()
        return ser.data

    def get_linked_users(self, obj):
        request = self.context.get('request')
        linked_users = []
        if obj.user_type == USER_TYPE_ATHLETE and request:
            coaches = []
            coach_teams = defaultdict(set)

            # one to one connections
            coaches.extend(list(obj.athleteuser.coaches.all()))

            # connections through teams
            for team in obj.athleteuser.team_membership.all():
                for coach in team.get_all_coaches():
                    coach_teams[coach.pk].add(team)
                    coaches.append(coach)

            coaches = self._filter_by_perms(obj, coaches)
            ctx = {'request': request, 'coach_teams': coach_teams}
            linked_users = AthleteCoachLinkedSerializer(set(coaches), many=True, context=ctx).data

        elif obj.user_type == USER_TYPE_COACH and request:
            athletes = []
            # one to one connections
            athletes.extend(list(obj.coachuser.athleteuser_set.all()))
            # connections through teams
            for team in (obj.coachuser.team_membership.all() | obj.team_ownership.all()).distinct():
                athletes.extend(team.get_all_athletes())

            athletes = self._filter_by_perms(obj, athletes)
            linked_users = AthleteCoachLinkedSerializer(set(athletes), many=True, context={"request": request}).data

        elif obj.user_type == USER_TYPE_ORG and request:
            org_members = obj.organisation.members.all()
            org_teams_athletes = (a.user for t in obj.organisation.teams.all() for a in t.athletes.all())
            org_teams_coaches = (c.user for t in obj.organisation.teams.all() for c in t.coaches.all())
            users = set(chain(org_members, org_teams_athletes, org_teams_coaches))
            linked_users = AthleteCoachLinkedSerializer(users, many=True, context={"request": request}).data
        return linked_users

    @staticmethod
    def _filter_by_perms(me, users):
        """ Leave only those users who are connected via permissions """
        qs = Coaching.objects.using(me.country)
        user_ids = {u.user.id for u in users}

        if me.user_type == USER_TYPE_ATHLETE:
            ids = set(qs.filter(athlete_id=me.id, coach_id__in=user_ids).values_list('coach_id', flat=True).distinct())
        else:
            ids = set(qs.filter(coach_id=me.id, athlete_id__in=user_ids).values_list('athlete_id', flat=True).distinct())

        return [u for u in users if u.user.id in ids]

    def get_team_memberships(self, obj):
        request = self.context.get('request')
        teams = []
        if obj.user_type == USER_TYPE_ATHLETE and request:
            teams = obj.athleteuser.team_membership.all()
        elif obj.user_type == USER_TYPE_COACH and request:
            teams = obj.coachuser.team_membership.all()
        elif obj.user_type == USER_TYPE_ORG and request:
            teams = obj.organisation.teams.all()
        return TeamMembershipOwnershipListSerializer(teams, many=True, context={"request": request}).data


class AthleteUserListSerializer(CustomUserListSerializer):
    """
    Serializer to list athlete profile.
    """
    referral_code = serializers.CharField(source='athleteuser.referral_code', required=False, allow_blank=True)
    athlete_terms_conditions = serializers.BooleanField(source='athleteuser.athlete_terms_conditions', required=False)

    class Meta(CustomUserListSerializer.Meta):
        fields = CustomUserListSerializer.Meta.fields + ('referral_code', 'athlete_terms_conditions',)


class AthleteUserCustomerListSerializer(AthleteUserListSerializer):
    """
    Serializer to list stripe customer profile (only for athlete user).
    """
    payment_status = serializers.CharField(source='athleteuser.customer.payment_status', read_only=True)

    class Meta(AthleteUserListSerializer.Meta):
        fields = AthleteUserListSerializer.Meta.fields + ('payment_status',)


class CoachUserListSerializer(CustomUserListSerializer):
    """
    Serializer to list coach profile.
    """
    team_ownerships = serializers.SerializerMethodField()

    def get_team_ownerships(self, obj):
        request = self.context.get('request')
        teams = []
        if obj.user_type == USER_TYPE_COACH and request:
            teams = obj.team_ownership.all()
        return TeamMembershipOwnershipListSerializer(teams, many=True, context={"request": request}).data

    class Meta(CustomUserListSerializer.Meta):
        fields = CustomUserListSerializer.Meta.fields + ('team_ownerships',)


class OrganisationUserListSerializer(CustomUserListSerializer):
    """
    Serializer to list organisation profile.
    """
    organisation_name = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    sports = serializers.SerializerMethodField()
    phone_number = serializers.CharField()
    team_ownerships = serializers.SerializerMethodField()

    def get_team_ownerships(self, obj):
        request = self.context.get('request')
        teams = []
        if obj.user_type == USER_TYPE_ORG and request:
            teams = obj.team_ownership.all()
        return TeamMembershipOwnershipListSerializer(teams, many=True, context={"request": request}).data

    def get_organisation_name(self, obj):
        return obj.organisation.name

    def get_size(self, obj):
        return obj.organisation.size

    def get_description(self, obj):
        return obj.organisation.description

    def get_sports(self, obj):
        return obj.organisation.sports

    class Meta(CustomUserListSerializer.Meta):
        fields = CustomUserListSerializer.Meta.fields + \
                 ('size', 'description', 'sports', 'phone_number', 'organisation_name', 'team_ownerships')


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ('id', 'name')
