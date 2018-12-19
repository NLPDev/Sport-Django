from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.models import TimeStampedModel


class BaseSportEngineModel(TimeStampedModel):
    sport_engine_id = models.PositiveIntegerField(primary_key=True, verbose_name=_('sport engine id'))
    data = JSONField()

    class Meta:
        abstract = True


class SportEngineTeam(BaseSportEngineModel):
    team = models.OneToOneField('multidb_account.Team', unique=True, related_name='sport_engine_team')

    class Meta:
        db_table = 'sport_engine_team'
        verbose_name_plural = _('teams')

    def __str__(self):
        return 'sport_engine_id=%i, team=%s' % (self.sport_engine_id, self.team)


class SportEngineGame(BaseSportEngineModel):
    sport_engine_teams = models.ManyToManyField(SportEngineTeam, related_name='sport_engine_games')
    athletes = models.ManyToManyField('multidb_account.AthleteUser', blank=True, related_name='sport_engine_games')

    class Meta:
        db_table = 'sport_engine_game'
        verbose_name_plural = _('games')

    def __str__(self):
        return 'sport_engine_id=%i, title=%s' % (self.sport_engine_id, self.data.title)


class SportEngineEvent(BaseSportEngineModel):
    sport_engine_team = models.ForeignKey(SportEngineTeam, related_name='sport_engine_events')
    sport_engine_game = models.ForeignKey(SportEngineGame, related_name='sport_engine_events', null=True, blank=True)
    athletes = models.ManyToManyField('multidb_account.AthleteUser', blank=True, related_name='sport_engine_events')

    class Meta:
        db_table = 'sport_engine_event'
        verbose_name_plural = _('events')

    def __str__(self):
        return self.sport_engine_id









class SportEngineEvent(BaseSportEngineModel):
    sport_engine_team = models.ForeignKey(SportEngineTeam, related_name='sport_engine_events')
    sport_engine_game = models.ForeignKey(SportEngineGame, related_name='sport_engine_events', null=True, blank=True)
    athletes = models.ManyToManyField('multidb_account.AthleteUser', blank=True, related_name='sport_engine_events')

    class Meta:
        db_table = 'sport_engine_event'
        verbose_name_plural = _('events')

    def __str__(self):
        return self.sport_engine_id