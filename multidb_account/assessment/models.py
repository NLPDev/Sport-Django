from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from multidb_account.sport.models import Sport
from multidb_account.constants import USER_TYPE_ATHLETE, USER_TYPE_COACH
from multidb_account.team.models import Team
from multidb_account.user.models import AthleteUser, CoachUser


class AssessmentTopCategory(models.Model):
    class Meta:
        db_table = 'multidb_account_assessment_top_category'
        verbose_name = 'Top Category'
        verbose_name_plural = 'Top Categories'

    name = models.CharField(verbose_name=_('assessment top category name'), max_length=255,
                            null=False, blank=False, unique=True)
    description = models.TextField(verbose_name=_('assessment top category description'), max_length=255, blank=True)
    sport = models.OneToOneField(Sport, null=True, blank=True)
    # help = models.ForeignKey(Help) TODO info box

    def __str__(self):
        return self.name


class AssessmentSubCategory(models.Model):
    class Meta:
        db_table = 'multidb_account_assessment_sub_category'
        verbose_name = 'Sub Category'
        verbose_name_plural = 'Sub Categories'

    name = models.CharField(verbose_name=_('assessment category name'), max_length=255,
                            null=False, blank=False)
    description = models.TextField(verbose_name=_('assessment category description'), max_length=255, blank=True)
    parent_top_category = models.ForeignKey(AssessmentTopCategory, null=True, blank=True)
    parent_sub_category = models.ForeignKey('self', null=True, blank=True)
    # help = models.ForeignKey(Help) TODO info box

    def __str__(self):
        return "{}: {}".format(self.parent_top_category or self.parent_sub_category, self.name)


class AssessmentRelationshipType(models.Model):
    class Meta:
        db_table = 'multidb_account_assessment_relationship_type'
        verbose_name = 'Relationship Type'
        verbose_name_plural = 'Relationship Types'

    description = models.CharField(verbose_name=_('assessment relationship type description'), max_length=255,
                                   blank=True)
    type = models.CharField(verbose_name=_('assessment relationship type'), max_length=50)

    def __str__(self):
        if self.type == 'self':
            return "Self Assessments: Assessments performed by the individual."
        if self.type == 'athlete_coach':
            return "Athlete - Coach: Data or assessments going from the athlete to the coach."
        if self.type == 'coach_athlete':
            return "Coach - Athlete: Data or assessments going from the coach to the athlete."


class AssessmentFormat(models.Model):
    class Meta:
        db_table = 'multidb_account_assessment_format'
        verbose_name = _('Metric format')
        verbose_name_plural = _('Metric formats')

    description = models.CharField(verbose_name=_('format description'), max_length=255, blank=True)
    unit = models.CharField(verbose_name=_('format unit'), max_length=50, null=False, blank=False)
    validation_regex = models.CharField(verbose_name=_('metric value validation regex'), max_length=500, null=True,
                                        blank=True)

    def __str__(self):
        return '{} ({})'.format(self.unit, self.description)


class Assessment(models.Model):
    name = models.CharField(verbose_name=_('assessment name'), max_length=255,
                            null=False, blank=False)
    description = models.TextField(verbose_name=_('assessment description'), max_length=255, blank=True)
    parent_sub_category = models.ForeignKey(AssessmentSubCategory)
    format = models.ForeignKey(AssessmentFormat)
    relationship_types = models.ManyToManyField(AssessmentRelationshipType, help_text=(
        'One thing that is unique with PSR is defining clear relationships between the assessments and users. '
        'There are three types.'
    ))
    is_private = models.BooleanField(default=False, blank=True)
    is_public_everywhere = models.BooleanField(
        default=False, blank=True, help_text='If set, treat it as a public one everywhere (teams, organisations, ...).')

    class Meta:
        ordering = ['name', ]
        verbose_name = _('Metric')
        verbose_name_plural = _('Metrics')

    def __unicode__(self):
        return self.name

    def __str__(self):
        private_string = '(P) ' if self.is_private else ''
        return '%s%s - %s' % (private_string, self.parent_sub_category, self.name)

    def get_top_category(self):
        obj = self.parent_sub_category
        while obj.parent_sub_category:
            obj = obj.parent_sub_category
        return obj.parent_top_category

    def is_relationship_type_valid(self, assessed, assessor):
        if assessor.get_user_type() == USER_TYPE_COACH and assessed.get_user_type() == USER_TYPE_ATHLETE:
            return self.relationship_types.filter(type="coach_athlete").exists()
        if assessor.get_user_type() == USER_TYPE_ATHLETE and assessed.get_user_type() == USER_TYPE_COACH:
            return self.relationship_types.filter(type="athlete_coach").exists()
        if assessor.id == assessed.id:
            return self.relationship_types.filter(type="self").exists()
        return False


class AssessorAssessedBase(models.Model):
    class Meta:
        abstract = True

    def get_user_type(self):
        if self.athlete_id is not None:
            return self.athlete.user.user_type
        if self.coach_id is not None:
            return self.coach.user.user_type
        return None

    def get_email(self):
        if self.athlete_id is not None:
            return self.athlete.user.email
        if self.coach_id is not None:
            return self.coach.user.email
        return None

    def get_user_id(self):
        if self.athlete_id is not None:
            return self.athlete.user.id
        if self.coach_id is not None:
            return self.coach.user.id
        return None

    def get_first_name(self):
        if self.athlete_id is not None:
            return self.athlete.user.first_name
        if self.coach_id is not None:
            return self.coach.user.first_name
        return None

    def get_last_name(self):
        if self.athlete_id is not None:
            return self.athlete.user.last_name
        if self.coach_id is not None:
            return self.coach.user.last_name
        return None

    def get_profile_picture_url(self):
        if self.athlete_id is not None:
            user = self.athlete.user
        if self.coach_id is not None:
            user = self.coach.user

        if user.profile_picture and user.profile_picture.url:
            return user.profile_picture.url

        return None

    def delete_all_assessment_permissions(self):
        self.assessmenttopcategorypermission_set.all().delete()




class Assessor(AssessorAssessedBase):
    athlete = models.OneToOneField(AthleteUser, null=True, blank=True, on_delete=models.CASCADE)
    coach = models.OneToOneField(CoachUser, null=True, blank=True, on_delete=models.CASCADE)

    def has_assessment_access(self, assessed, top_category):
        # Always access if itself
        if self.id == assessed.id:
            return True
        else:
            return self.assessmenttopcategorypermission_set.filter(assessed=assessed,
                                                                   assessment_top_category=top_category,
                                                                   assessor_has_access=True).exists()

    def __str__(self):
        return 'Assessor: {}'.format(str(self.athlete or self.coach))


class Assessed(AssessorAssessedBase):
    athlete = models.OneToOneField(AthleteUser, null=True, blank=True, on_delete=models.CASCADE)
    coach = models.OneToOneField(CoachUser, null=True, blank=True, on_delete=models.CASCADE)
    assessments = models.ManyToManyField(Assessment, through='ChosenAssessment')

    def __str__(self):
        return 'Assessed: {}'.format(str(self.athlete or self.coach))


class ChosenAssessment(models.Model):

    class Meta:
        db_table = 'multidb_account_chosen_assessment'

    assessed = models.ForeignKey(Assessed, on_delete=models.CASCADE)
    assessor = models.ForeignKey(Assessor, on_delete=models.CASCADE)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, null=True)
    date_assessed = models.DateTimeField(verbose_name=_('date assessed'), default=timezone.now)
    value = models.DecimalField(verbose_name=_('assessment value'), max_digits=15, decimal_places=6)

    def __str__(self):
        return self.assessment.name


class AssessmentTopCategoryPermission(models.Model):
    class Meta:
        db_table = 'multidb_account_assessment_top_category_permission'

    assessed = models.ForeignKey(Assessed, on_delete=models.CASCADE)
    assessor = models.ForeignKey(Assessor, on_delete=models.CASCADE)
    assessment_top_category = models.ForeignKey(AssessmentTopCategory, on_delete=models.CASCADE)
    assessor_has_access = models.BooleanField(verbose_name=_('assessor has access'), default=False)

