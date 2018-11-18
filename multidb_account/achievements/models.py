from django.conf import settings as django_settings
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Badge(models.Model):
    image_url = models.ImageField(verbose_name=_('image'), null=True, blank=True, max_length=512)
    name = models.CharField(verbose_name=_('name'), max_length=255, null=True, blank=True)


class Achievement(models.Model):
    title = models.TextField(verbose_name=_('title'))
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, verbose_name=_('created by'),
                                   on_delete=models.CASCADE)
    competition = models.TextField(verbose_name=_('competition'))
    team = models.CharField(max_length=140, blank=True, null=True, verbose_name=_('team'))
    date = models.DateField(verbose_name=_('date'))
    badge = models.ForeignKey(Badge, verbose_name=_('badge'), on_delete=models.CASCADE)
