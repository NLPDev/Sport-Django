import re
from datetime import timedelta
from statistics import mean

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings as django_settings
from rest_framework import serializers

from multidb_account.constants import USER_TYPE_ATHLETE, USER_TYPE_COACH
from multidb_account.team.models import Team
from multidb_account.assessment.models import AssessmentTopCategory, AssessmentSubCategory, \
    ChosenAssessment, Assessed, Assessment, AssessmentTopCategoryPermission, AssessmentRelationshipType

UserModel = get_user_model()


class AssessedListSerializer(serializers.ModelSerializer):
    """
    Assessed Serializer.
    """
    id = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.get_user_id()

    def get_email(self, obj):
        return obj.get_email()

    def get_first_name(self, obj):
        return obj.get_first_name()

    def get_last_name(self, obj):
        return obj.get_last_name()

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.get_profile_picture_url() and request:
            return request.build_absolute_uri(obj.get_profile_picture_url())
        return ''

    class Meta:
        model = Assessed
        fields = ('id', 'email', 'first_name', 'last_name', 'profile_picture_url')


# ---------------------Assessment-------------------------


class AssessmentsTreeListSerializer(serializers.ModelSerializer):
    childs = serializers.SerializerMethodField()
    is_flat = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentSubCategory
        fields = ('id', 'name', 'description', 'childs', 'is_flat')

    def get_childs(self, obj):
        if isinstance(obj, AssessmentTopCategory):
            # it's a top category without assessments objects
            return AssessmentsTreeListSerializer(
                self._filter_subcats(obj.assessmentsubcategory_set.all()), many=True, context=self.context).data

        if isinstance(obj, AssessmentSubCategory):
            if obj.assessment_set.exists():
                # it's a sub category with assessments objects
                return AssessmentSerializer(
                    self._filter_assessments(obj.assessment_set.all()), many=True, context=self.context).data
            else:
                # it's a category without assessments objects
                return AssessmentsTreeListSerializer(
                    self._filter_subcats(obj.assessmentsubcategory_set.all()), many=True, context=self.context).data

    def get_is_flat(self, obj):
        # render is_flat = True only for sub_categories with assessments objects and right below a top category
        if isinstance(obj, AssessmentSubCategory) and obj.parent_top_category_id is not None:
            if obj.assessment_set.all():
                return True
        return False

    def _filter_subcats(self, qs):
        """ Filter subcategories based on org privacy """
        subcat_ids = self.context['subcat_ids']
        return qs.filter(id__in=subcat_ids)

    def _filter_assessments(self, qs):
        """ Filter subcategory's assessments based on org/team privacy """
        user = self.context['request'].user
        user_from_own_assessments_only_org = self.context['user_from_own_assessments_only_org']
        my_org_private = Q(organisations__members=user) | Q(organisations__login_users=user)
        public = Q(is_public_everywhere=True)
        public = public | (Q() if user_from_own_assessments_only_org else Q(is_private=False))

        if user.user_type == USER_TYPE_ATHLETE:
            my_team_private = Q(is_private=True, teams__athletes=user.athleteuser)
            my_org_private = my_org_private | Q(organisations__teams__athletes=user.athleteuser)
        elif user.user_type == USER_TYPE_COACH:
            my_team_private = Q(is_private=True) & (Q(teams__coaches=user.coachuser) | Q(teams__owner=user))
            my_org_private = my_org_private | Q(organisations__teams__coaches=user.coachuser)
        else:
            my_team_private = Q()

        return qs.filter(public | my_team_private | my_org_private).distinct()


class ChosenAssessmentTreeListSerializer(serializers.ModelSerializer):
    """
    Serializer to list assessed's assessments rendered through the assessment reference tree.
    """
    childs = serializers.SerializerMethodField()
    is_flat = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentSubCategory
        fields = ('id', 'name', 'description', 'childs', 'is_flat')

    def get_childs(self, obj):
        # Here we generate the Assessed's assessments tree based on the assessments global tree
        queryset = self.context['queryset']  # of ChosenAssessment
        get_averages = self.context.get('get_averages')

        if isinstance(obj, AssessmentTopCategory):
            return ChosenAssessmentTreeListSerializer(obj.assessmentsubcategory_set.all(), many=True,
                                                      context=self.context).data
        if isinstance(obj, AssessmentSubCategory):
            if obj.assessment_set.all():
                # it's a sub category with assessments objects
                assessments = obj.assessment_set.all().order_by('id')
                chosen_assessments = []
                for assessment in assessments:
                    values = queryset.filter(assessment_id=assessment.id)
                    if values:
                        if get_averages:
                            values = self._get_average(values)
                            data = ChosenAssessmentAveragesSerializer(values, many=True).data
                        else:
                            data = ChosenAssessmentListSerializer(values, many=True).data
                        chosen_assessments.append(data)
                return chosen_assessments
            else:
                # it's a category without assessments objects
                return ChosenAssessmentTreeListSerializer(obj.assessmentsubcategory_set.all(), many=True,
                                                          context={'queryset': queryset}).data

    @staticmethod
    def _get_average(values):
        avg = mean([v.value for v in values])
        return [ChosenAssessment(
            assessment=values[0].assessment,
            team=values[0].team,
            value=avg,
        )]

    def get_is_flat(self, obj):
        # render is_flat = True only for sub_categories with assessments objects and right below a top category
        if isinstance(obj, AssessmentSubCategory) and obj.parent_top_category_id is not None:
            if obj.assessment_set.all():
                return True
        return False


class AssessmentRelationshipTypeSerializer(serializers.ModelSerializer):
    """
    Assessment relationship types Serializer.
    """

    class Meta:
        model = AssessmentRelationshipType
        fields = ('type',)


class AssessmentSerializer(serializers.ModelSerializer):
    """
    Assessment Serializer.
    """
    format_description = serializers.CharField(source='format.description')
    unit = serializers.CharField(source='format.unit')
    relationship_types = AssessmentRelationshipTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Assessment
        fields = ('id', 'name', 'description', 'relationship_types', 'format_description', 'unit', 'is_private')


# ---------------------ChosenAssessment-------------------------


class ChosenAssessmentListSerializer(serializers.ModelSerializer):
    """
    Serializer to list assessed's assessments.
    """

    class Meta:
        model = ChosenAssessment
        fields = ('id', 'assessed_id', 'team_id', 'assessor_id', 'assessment_id', 'value', 'date_assessed')


class ChosenAssessmentAveragesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChosenAssessment
        fields = ('assessment_id', 'value')


class ChosenAssessmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer to create assessed's assessments.
    """
    assessment_id = serializers.IntegerField(required=False)
    value = serializers.DecimalField(max_digits=15, decimal_places=6, required=False)

    team_id = serializers.IntegerField(required=False, allow_null=True)
    assessed_id = serializers.IntegerField(required=False)

    assessor_id = serializers.IntegerField(read_only=True)
    date_assessed = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ChosenAssessment
        fields = ('id', 'team_id', 'assessed_id', 'assessor_id', 'assessment_id', 'value', 'date_assessed')

    def create(self, validated_data):
        chosen_assessment = ChosenAssessment(assessor_id=self.assessor.id,
                                             assessed_id=validated_data.get('assessed_id'),
                                             team_id=validated_data.get('team_id'),
                                             assessment_id=validated_data.get('assessment_id'),
                                             value=validated_data.get('value'))

        chosen_assessment.save(using=self.localized_db)
        return chosen_assessment

    def validate(self, data):

        self.assessor = self.context['user'].get_assessor()
        self.localized_db = self.context['country']

        data['assessed_id'] = self.context['assessed_id'] if self.context['assessed_id'] else data.get('assessed_id')
        data['team_id'] = self.context['team_id'] if self.context['team_id'] else data.get('team_id')

        try:
            assessed = Assessed.objects.using(self.localized_db).get(id=data.get('assessed_id'))
            data['assessed_id'] = assessed.id
        except Assessed.DoesNotExist:
            raise serializers.ValidationError(_("Invalid"))

        # validate if the athlete is able to assess the coach according to `settings.ATHLETE_COACH_ASSESSMENT_TIMEOUT`
        if self.assessor.get_user_type() == USER_TYPE_ATHLETE and \
                self.assessor.get_user_id() != assessed.get_user_id() and \
                assessed.coach is not None:

            timeout_dt = timezone.now() - timedelta(seconds=django_settings.ATHLETE_COACH_ASSESSMENT_TIMEOUT)
            too_soon = assessed.assessments.using(self.localized_db) \
                .filter(chosenassessment__date_assessed__gte=timeout_dt).exists()

            if too_soon:
                raise serializers.ValidationError(
                    {"assessed_id": _("You can only assess a coach's leadership skills once every month")})

            if self.context.get('dry_run'):
                return data

        try:
            assessment = Assessment.objects.using(self.localized_db).get(id=data.get('assessment_id'))
        except Assessment.DoesNotExist:
            raise serializers.ValidationError(_("Invalid"))

        if data['team_id']:
            try:
                data['team_id'] = Team.objects.using(self.localized_db).get(id=data.get('team_id')).id
            except Team.DoesNotExist:
                raise serializers.ValidationError({"team_id": _("Unknown team")})
        else:
            data['team_id'] = None

        # validate if assessed and assessor are connected.
        # self.context['user'] is the assessor
        if self.assessor.get_user_id() != assessed.get_user_id() and not \
                self.context['user'].is_connected_to(assessed.get_user_id()):
            raise serializers.ValidationError({"error": _("Users are not connected")})

        # validate if an assessor can access this assessment.
        if not self.assessor.has_assessment_access(assessed, assessment.get_top_category()):
            raise serializers.ValidationError({"assessment_id": _("Assessor is not allowed to access this assessment")})

        # validate if the assessment relationship type is valid.
        if not assessment.is_relationship_type_valid(assessed, self.assessor):
            raise serializers.ValidationError({"error": _("Relationship can't be accessed by the current assessor")})

        # validate the value format
        if not bool(re.match(assessment.format.validation_regex, str(data.get('value')))):
            raise serializers.ValidationError({"value": _("Wrong value format. {}").
                                              format(assessment.format.description)})
        return data


class ChosenAssessmentUpdateSerializer(serializers.Serializer):
    """
    Serializer to update assessed's assessments.
    """
    id = serializers.IntegerField(required=True)
    value = serializers.DecimalField(max_digits=15, decimal_places=6, required=True)

    team_id = serializers.IntegerField(read_only=True)
    assessment_id = serializers.IntegerField(read_only=True)
    assessor_id = serializers.IntegerField(read_only=True)
    assessed_id = serializers.IntegerField(read_only=True)
    date_assessed = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        # create is called here because we don't pass an instance but a list of instances, that the only way for now
        # to update a list of instances at the same time
        # TODO: This should be refactored in the futur

        instance = ChosenAssessment.objects.using(self.localized_db).get(id=validated_data.get('id'))
        instance.value = validated_data.get('value', instance.value)
        instance.save()
        return instance

    def validate(self, data):
        self.assessor = self.context['user'].get_assessor()
        self.localized_db = self.context['country']
        assessed_id = self.context['assessed_id']

        try:
            self.assessed = Assessed.objects.using(self.localized_db).get(id=assessed_id)
        except Assessed.DoesNotExist:
            raise serializers.ValidationError(_("Invalid"))

        try:
            chosen_assessment = ChosenAssessment.objects.using(self.localized_db).get(id=data.get('id'))
        except ChosenAssessment.DoesNotExist:
            raise serializers.ValidationError(_("Invalid"))

        # validate if assessed and assessor are connected.
        # self.context['user'] is the assessor
        if self.assessor.get_user_id() != self.assessed.get_user_id() and not \
                self.context['user'].is_connected_to(self.assessed.get_user_id()):
            raise serializers.ValidationError({"error": _("Users are not connected")})

        # validate if an assessor can access this assessment.
        if not self.assessor.has_assessment_access(self.assessed, chosen_assessment.assessment.get_top_category()):
            raise serializers.ValidationError({"error": _("Assessor is not allowed to access this assessment")})

        # validate if the assessment relationship type is valid.
        if not chosen_assessment.assessment.is_relationship_type_valid(self.assessed, self.assessor):
            raise serializers.ValidationError({"error": _("Relationship can't be accessed by the current assessor")})

        # validate the value format
        if not bool(re.match(chosen_assessment.assessment.format.validation_regex, str(data.get('value')))):
            raise serializers.ValidationError({"error": _("Wrong value format. {}").
                                              format(chosen_assessment.assessment.format.description)})

        return data


class AssessmentTopCategorySerializer(serializers.Serializer):
    """
    Serializer to list assessment top categories.
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)

    class Meta:
        model = AssessmentTopCategory
        fields = ('id', 'name',)


class TeamChosenAssessmentListSerializer(serializers.ModelSerializer):
    """
    Serializer to list assessed's assessments.
    """
    unit = serializers.CharField(source='assessment.format.unit')
    assessed = AssessedListSerializer(read_only=True)

    class Meta:
        model = ChosenAssessment
        fields = ('id', 'assessed', 'team_id', 'assessor_id', 'assessment_id', 'value', 'date_assessed', 'unit')


# ------------------------------AssessmentTopCategoryPermission-----------------------------------------------


class AssessmentTopCategoryPermissionListSerializer(serializers.ModelSerializer):
    """
    Serializer to list assessed's assessment permissions.
    """
    assessment_top_category_name = serializers.CharField(source='assessment_top_category.name', read_only=True)

    class Meta:
        model = AssessmentTopCategoryPermission
        fields = ('id', 'assessed_id', 'assessor_id', 'assessment_top_category_id', 'assessment_top_category_name',
                  'assessor_has_access')


class AssessmentTopCategoryPermissionUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer to update assessed's assessment permissions.
    """
    assessor_id = serializers.IntegerField(required=True)
    assessment_top_category_id = serializers.IntegerField(required=True)
    assessor_has_access = serializers.BooleanField(required=True)

    assessed_id = serializers.IntegerField(read_only=True)
    assessment_top_category_name = serializers.CharField(source='assessment_top_category.name', read_only=True)

    class Meta:
        model = AssessmentTopCategoryPermission
        fields = ('id', 'assessed_id', 'assessor_id', 'assessment_top_category_id', 'assessment_top_category_name',
                  'assessor_has_access')

    def create(self, validated_data):
        # create is called here because we don't pass an instance but a list of instances, that the only way for now
        #  to update a list of instances at the same time
        # TODO: This should be refactored in the futur

        self.localized_db = self.context['country']
        assessed_id = self.context['assessed_id']

        instance = AssessmentTopCategoryPermission.objects. \
            using(self.localized_db).get(assessed_id=assessed_id,
                                         assessor_id=validated_data.get('assessor_id'),
                                         assessment_top_category_id=validated_data.get('assessment_top_category_id'))

        instance.assessor_has_access = validated_data.get('assessor_has_access', instance.assessor_has_access)
        instance.save()
        return instance

    def validate(self, data):
        self.localized_db = self.context['country']
        assessed_id = self.context['assessed_id']

        try:
            UserModel.objects.using(self.localized_db).get(pk=data.get('assessor_id'))
        except UserModel.DoesNotExist:
            raise serializers.ValidationError({"assessor_id": _("Unknown assessor id: {}".
                                                                format(data.get('assessor_id')))})

        try:
            AssessmentTopCategoryPermission.objects. \
                using(self.localized_db).get(assessed_id=assessed_id,
                                             assessor_id=data.get('assessor_id'),
                                             assessment_top_category_id=data.get('assessment_top_category_id'))
        except AssessmentTopCategoryPermission.DoesNotExist:
            raise serializers.ValidationError({"assessment_top_category_id":
                                                   _("Unknown Assessment Top Category Permission id: {}".
                                                     format(data.get('assessment_top_category_id')))})
        return data



