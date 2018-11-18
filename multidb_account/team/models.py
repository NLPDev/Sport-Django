from functools import partial

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from imagekit.models import ProcessedImageField
from pilkit.processors import SmartResize, Transpose

from multidb_account.choices import TEAM_STATUSES
from multidb_account.constants import PROFILE_PICTURE_WIDTH, PROFILE_PICTURE_HEIGHT
from multidb_account.constants import USER_TYPE_ATHLETE, USER_TYPE_COACH, TEAM_STATUS_ACTIVE
from multidb_account.models import get_file_path
from multidb_account.sport.models import Sport
from multidb_account.user.models import AthleteUser, CoachUser, Organisation, BaseCustomUser


class Team(models.Model):
    name = models.CharField(verbose_name=_('team name'), max_length=255)
    status = models.CharField(verbose_name=_('team status'), choices=TEAM_STATUSES, max_length=30,
                              default=TEAM_STATUS_ACTIVE)

    team_picture = ProcessedImageField(verbose_name=_('profile picture'),
                                       upload_to=partial(get_file_path, path='team/'),
                                       null=True,
                                       blank=True,
                                       processors=[
                                           Transpose(Transpose.AUTO),
                                           SmartResize(PROFILE_PICTURE_WIDTH, PROFILE_PICTURE_HEIGHT),
                                       ],
                                       options={'quality': 100})

    tagline = models.TextField(verbose_name=_('team tagline'), max_length=500, blank=True)
    location = models.CharField(verbose_name=_('team location'), max_length=255, blank=True)
    season = models.CharField(verbose_name=_('season'), max_length=25, blank=True)
    owner = models.ForeignKey(BaseCustomUser, related_name='team_ownership')
    sport = models.ForeignKey(Sport)
    athletes = models.ManyToManyField(AthleteUser, related_name='team_membership')
    coaches = models.ManyToManyField(CoachUser, related_name='team_membership')
    date_created = models.DateField(verbose_name=_('date created'), default=timezone.now)
    is_private = models.BooleanField(verbose_name=_('is private'), default=False, blank=True)
    organisation = models.ForeignKey(Organisation, verbose_name=_('organisation'), null=True, blank=True,
                                     related_name='teams')
    assessments = models.ManyToManyField('multidb_account.Assessment', verbose_name=_('private assessments'),
                                         related_name='teams')

    def __str__(self):
        return self.name

    def add_baseuser(self, base_user):
        if base_user.user_type == USER_TYPE_COACH:
            self.coaches.add(base_user.typeduser)
        if base_user.user_type == USER_TYPE_ATHLETE:
            self.athletes.add(base_user.typeduser)

    def get_all_coaches(self):
        return list(self.coaches.all())

    def get_all_athletes(self):
        return list(self.athletes.all())

    def get_all_members(self):
        return self.get_all_athletes() + self.get_all_coaches()

    def has_team_member(self, user: CoachUser or AthleteUser):
        return user in self.get_all_members()
