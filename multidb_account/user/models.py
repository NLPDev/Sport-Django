from functools import partial

from django.conf import settings as django_settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.core import signing
from django.core.mail import send_mail
from django.core.validators import RegexValidator
from django.db import models
from django.template import loader
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from imagekit.models import ProcessedImageField
from pilkit.processors import SmartResize, Transpose

from multidb_account.choices import MEASURING, USER_TYPES, ORG_SIZES
from multidb_account.constants import PROFILE_PICTURE_WIDTH, PROFILE_PICTURE_HEIGHT, USER_CONFIRM_ACCOUNT_SALT, \
    USER_TYPE_ORG
from multidb_account.constants import USER_TYPE_ATHLETE, USER_TYPE_COACH
from multidb_account.managers import CustomUserManager
from multidb_account.models import get_file_path


class BaseCustomUser(AbstractBaseUser, PermissionsMixin):
    # Required fields
    email = models.EmailField(verbose_name=_('email address'), max_length=255, unique=True)
    country = models.CharField(verbose_name=_('country iso code'), max_length=7)

    # Optional fields
    province_or_state = models.CharField(verbose_name=_('province or state'), max_length=64, blank=True)
    city = models.CharField(verbose_name=_('city'), max_length=64, blank=True)
    first_name = models.CharField(verbose_name=_('first name'), max_length=128)
    last_name = models.CharField(verbose_name=_('last name'), max_length=128)
    date_of_birth = models.DateField(verbose_name=_('date of birth'), null=True, blank=True)
    newsletter = models.BooleanField(verbose_name=_('newsletter opt-in'), default=False)
    terms_conditions = models.BooleanField(verbose_name=_('terms and conditions agreement'), default=False)
    measuring_system = models.CharField(verbose_name=_('preferred measurind system'),
                                        choices=MEASURING, max_length=30, default='metric')

    profile_picture = ProcessedImageField(verbose_name=_('profile picture'),
                                          upload_to=partial(get_file_path, path='profile/'),
                                          null=True,
                                          blank=True,
                                          processors=[
                                              Transpose(Transpose.AUTO),
                                              SmartResize(PROFILE_PICTURE_WIDTH, PROFILE_PICTURE_HEIGHT),
                                          ],
                                          options={'quality': 100})

    tagline = models.TextField(verbose_name=_('tagline'), max_length=500, blank=True)
    is_active = models.BooleanField(verbose_name=_('active'), default=True)
    is_staff = models.BooleanField(verbose_name=_('staff status'), default=False)
    is_admin = models.BooleanField(verbose_name=_('superuser'), default=False)
    jwt_last_expired = models.DateTimeField(default=timezone.now)
    user_type = models.CharField(verbose_name=_('user type'), choices=USER_TYPES, max_length=50,
                                 default=USER_TYPE_ATHLETE)
    date_joined = models.DateTimeField(verbose_name=_('date joined'), default=timezone.now)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_('Phone number must be 9 to 15 digits entered in the format "+999999999" where "+" is optional'))
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    new_dashboard = models.BooleanField(verbose_name=_('new dashboard'), default=False)

    objects = CustomUserManager()

    def __unicode__(self):
        return self.email

    def __str__(self):
        return '%s %s <%s>' % (self.first_name, self.last_name, self.email)

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['country']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    @property
    def profile_complete(self):
        """Return the profile complete status."""
        if self.user_type == USER_TYPE_ORG:
            return True
        return self.email and \
            self.country and \
            self.user_type and \
            self.province_or_state and \
            self.city and \
            self.first_name and \
            self.last_name and \
            self.date_of_birth and \
            self.terms_conditions and \
            self.tagline

    def get_full_name(self):
        """Return the email."""
        return self.email

    def get_short_name(self):
        """Return the email."""
        return self.email

    def set_jwt_last_expired(self):
        self.jwt_last_expired = timezone.now()

    def deactivate(self):
        # Deactivate all JWT tokens
        self.set_jwt_last_expired()
        # Disable user
        self.is_active = False
        self.save()

    @property
    def typeduser(self):
        """ Returns typed instance of the user """

        if self.user_type == USER_TYPE_ATHLETE:
            return self.athleteuser
        if self.user_type == USER_TYPE_COACH:
            return self.coachuser
        if self.user_type == USER_TYPE_ORG:
            return self.organisation

    def is_athlete(self):
        """ Get the user's assessor profile extension """
        return self.user_type == USER_TYPE_ATHLETE

    def is_coach(self):
        """ Get the user's assessor profile extension """
        return self.user_type == USER_TYPE_COACH

    def is_organisation(self):
        return self.user_type == USER_TYPE_ORG

    def get_assessor(self):
        """ Get the user's assessor profile extension """

        return self.typeduser.assessor

    def get_assessed(self):
        """ Get the user's assessed profile extension """

        return self.typeduser.assessed

    def is_connected_to(self, other_user_id):

        if self.user_type == USER_TYPE_ATHLETE:
            # Check if athlete is directly connected (Coaching) or connected through teams (Team)
            return self.athleteuser.coaching_set.filter(coach_id=other_user_id).exists() or \
                   self.athleteuser.team_membership.filter(coaches__user__id=other_user_id).exists() or \
                   self.athleteuser.team_membership.filter(owner_id=other_user_id)

        if self.user_type == USER_TYPE_COACH:
            # Check if coach is directly connected (Coaching) or connected through teams (Team)
            return self.coachuser.coaching_set.filter(athlete_id=other_user_id).exists() or \
                   self.team_ownership.filter(athletes__user__id=other_user_id).exists() or \
                   self.coachuser.team_membership.filter(athletes__user__id=other_user_id).exists()

        if self.user_type == USER_TYPE_ORG:
            # Check if organisation is directly connected or connected through teams
            return self.team_ownership.filter(athletes__user__id=other_user_id).exists() or \
                   self.organisation.teams.filter(athletes__user__id=other_user_id).exists() or \
                   self.organisation.teams.filter(coaches__user__id=other_user_id).exists()

    def delete_all_connections(self):
        # Delete all user's connections
        self.typeduser.assessed.delete_all_assessment_permissions()
        self.typeduser.assessor.delete_all_assessment_permissions()
        self.typeduser.coaching_set.all().delete()
        return True

    def send_welcome_email(self):
        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'api_site': django_settings.PSR_API_BASE_URL,
            'user': self,
            # 'secure': self.request.is_secure(),
        }

        msg_plain = loader.render_to_string(django_settings.WELCOME_EMAIL_TEMPLATE + '.txt', context)
        msg_html = loader.render_to_string(django_settings.WELCOME_EMAIL_TEMPLATE + '.html', context)

        subject = _("Welcome to Personal Sport Record")
        send_mail(subject,
                  msg_plain,
                  django_settings.DEFAULT_FROM_EMAIL,
                  [self.email],
                  html_message=msg_html)

    def send_confirm_account_email(self):
        data = {
            'user_id': self.id,
            'localized_db': self.country,
        }

        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'api_site': django_settings.PSR_API_BASE_URL,
            'confirm_account_path': django_settings.PSR_APP_CONFIRM_ACCOUNT_PATH,
            'user': self,
            'token': signing.dumps(data, salt=USER_CONFIRM_ACCOUNT_SALT),
            # 'secure': self.request.is_secure(),
        }

        msg_plain = loader.render_to_string(django_settings.CONFIRM_ACCOUNT_EMAIL_TEMPLATE + '.txt', context)
        msg_html = loader.render_to_string(django_settings.CONFIRM_ACCOUNT_EMAIL_TEMPLATE + '.html', context)

        subject = _("Confirm the email of your Personal Sport Record account")
        send_mail(subject, msg_plain, django_settings.DEFAULT_FROM_EMAIL, [self.email], html_message=msg_html)

    def get_linked_users(self):
        if self.user_type == USER_TYPE_ATHLETE:
            coaches = []
            # one to one connections
            coaches.extend(list(self.athleteuser.coaches.all()))
            # connections through teams
            for team in self.athleteuser.team_membership.all():
                coaches.extend(team.get_all_coaches())
            return set(coaches)

        elif self.user_type == USER_TYPE_COACH:
            athletes = []
            # one to one connections
            athletes.extend(list(self.coachuser.athleteuser_set.all()))
            # connections through teams
            for team in (self.coachuser.team_membership.all() | self.team_ownership.all()).distinct():
                athletes.extend(team.get_all_athletes())
            return set(athletes)

    @cached_property
    def organisation(self):
        return self.organisations.first()


class AthleteCoachBase(models.Model):
    class Meta:
        abstract = True

    def get_assessor(self):
        return self.assessor

    def get_assessed(self):
        return self.assessed

    def __str__(self):
        return str(self.id)

    @property
    def full_name(self):
        return "{} {}".format(self.user.first_name, self.user.last_name)


class CoachUser(AthleteCoachBase):
    class Meta:
        db_table = 'multidb_account_coach_user'

    user = models.OneToOneField(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)

    def __str__(self):
        return str(self.user)


class AthleteUser(AthleteCoachBase):
    class Meta:
        db_table = 'multidb_account_athlete_user'

    user = models.OneToOneField(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)

    # additional fields
    referral_code = models.CharField(verbose_name=_('referral_code'), max_length=255, blank=True)
    promocode = models.CharField(verbose_name=_('promocode'), max_length=32, blank=True)
    athlete_terms_conditions = models.BooleanField(verbose_name=_('terms and conditions agreement'), default=False)
    coaches = models.ManyToManyField(CoachUser, through='Coaching')

    def __str__(self):
        return str(self.user)


class Coaching(models.Model):
    athlete = models.ForeignKey(AthleteUser, on_delete=models.CASCADE)
    coach = models.ForeignKey(CoachUser, on_delete=models.CASCADE)
    date_joined = models.DateField(verbose_name=_('date joined'), default=timezone.now)

    @classmethod
    def create_if_not_exist(cls, localized_db, athlete, coach):
        if not cls.objects.using(localized_db).filter(athlete=athlete, coach=coach).exists():
            cls.objects.using(localized_db).get_or_create(athlete=athlete, coach=coach)


class Organisation(models.Model):
    login_users = models.ManyToManyField(django_settings.AUTH_USER_MODEL, related_name='organisations')
    name = models.CharField(verbose_name=_('organisation name'), max_length=255)
    size = models.IntegerField(verbose_name=_('organisation size'), choices=ORG_SIZES, null=True, blank=True)
    description = models.TextField(verbose_name=_('description'), blank=True)
    sports = ArrayField(models.CharField(verbose_name=_('sports'), max_length=128), default=list, null=True, blank=True)
    members = models.ManyToManyField(django_settings.AUTH_USER_MODEL, verbose_name=_('organisation members'),
                                     related_name='member_of_organisations', blank=True)
    own_assessments = models.ManyToManyField(
        'multidb_account.Assessment', related_name='organisations', verbose_name=_('own assessments'), blank=True,
        help_text=_('Those are either '
                    '<br>a) <b>extra items</b> shown together with other public items '
                    '(when "Own assessments only" disabled) '
                    '<br>b) or <b>the only items</b> shown (when "Own assessments only" enabled).<br>'))
    own_assessments_only = models.BooleanField(verbose_name=_('own assessments only'), default=False,
                                               help_text=_('Whether to show only own assessments.'))

    class Meta:
        db_table = 'multidb_account_organisation'
        verbose_name_plural = _('organisations')

    def __str__(self):
        return self.name
