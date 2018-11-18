from django.db import models
from django.utils.translation import ugettext_lazy as _
from multidb_account.user.models import AthleteUser
from multidb_account.team.models import Team


class PreCompetition(models.Model):
    title = models.CharField(max_length=255, verbose_name=_('title'))
    goal = models.CharField(max_length=255, blank=True, verbose_name=_('title'))
    athlete = models.ForeignKey(AthleteUser, verbose_name=_('athlete'), on_delete=models.CASCADE)
    team = models.ForeignKey(Team, blank=True, null=True, verbose_name=_('team'))
    date = models.DateField(verbose_name=_('date'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('date created'))
    stress = models.PositiveSmallIntegerField(verbose_name=_('stress'))
    fatigue = models.PositiveSmallIntegerField(verbose_name=_('fatigue'))
    hydration = models.PositiveSmallIntegerField(verbose_name=_('hydration'))
    injury = models.PositiveSmallIntegerField(verbose_name=_('injury'))
    weekly_load = models.PositiveSmallIntegerField(verbose_name=_('weekly load'))


