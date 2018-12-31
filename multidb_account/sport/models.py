from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class Sport(models.Model):
    name = models.CharField(verbose_name=_('sport name'), max_length=128, unique=True)
    description = models.TextField(verbose_name=_('sport description'), max_length=500, blank=True)
    is_available = models.BooleanField(verbose_name=_('sport is available'), default=True)
    users = models.ManyToManyField(django_settings.AUTH_USER_MODEL, through='ChosenSport')

    def __str__(self):  # __unicode__ on Python 2
        return self.name


class ChosenSport(models.Model):
    class Meta:
        db_table = 'multidb_account_chosen_sport'

    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(verbose_name=_('date joined'), default=timezone.now)
    is_chosen = models.BooleanField(verbose_name=_('is sport chosen on profile'), default=False)
    is_displayed = models.BooleanField(verbose_name=_('is sport displayed on profile'), default=False)

    def __str__(self):  # __unicode__ on Python 2
        return self.sport.name


