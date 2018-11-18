from django.conf import settings as django_settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from multidb_account.team.models import Team
from multidb_account.user.models import AthleteUser, CoachUser


class File(models.Model):
    owner = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='files/%Y/%m/%d/%H/%M/%S', max_length=512)
    date_created = models.DateField(auto_now_add=True, verbose_name=_('date created'))


class Link(models.Model):
    url = models.CharField(verbose_name=_('url'), max_length=512, unique=True,
                           validators=[
                               RegexValidator(regex=r'(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)?[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?'),
                           ])

    def __str__(self):
        return self.url


class ReturnToPlayType(models.Model):
    value = models.CharField(primary_key=True, verbose_name=_('value'), max_length=64)

    def __str__(self):
        return self.value


class AthleteNote(models.Model):
    owner = models.ForeignKey(AthleteUser, verbose_name=_('owner'), on_delete=models.CASCADE)
    title = models.CharField(verbose_name=_('title'), max_length=255)
    return_to_play_type = models.ForeignKey(ReturnToPlayType, verbose_name=_('return to play type'),
                                            on_delete=models.CASCADE, null=True, blank=True)
    note = models.TextField(verbose_name=_('note'), blank=True, null=True)
    links = models.ManyToManyField(Link)
    files = models.ManyToManyField(File)
    date_created = models.DateField(auto_now_add=True, verbose_name=_('date created'))
    only_visible_to = models.ManyToManyField(CoachUser)  # Empty list means `visible to everyone`


class CoachNote(models.Model):
    owner = models.ForeignKey(CoachUser, verbose_name=_('owner'), on_delete=models.CASCADE)
    title = models.CharField(verbose_name=_('title'), max_length=255)
    athlete = models.ForeignKey(AthleteUser, blank=True, null=True, verbose_name=_('athlete'), on_delete=models.CASCADE)
    team = models.ForeignKey(Team, blank=True, null=True, verbose_name=_('team'))
    note = models.TextField(verbose_name=_('note'), blank=True, null=True)
    links = models.ManyToManyField(Link)
    files = models.ManyToManyField(File)
    date_created = models.DateField(auto_now_add=True, verbose_name=_('date created'))
