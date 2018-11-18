from django.conf import settings as django_settings
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Goal(models.Model):
    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, verbose_name=_('user'), on_delete=models.CASCADE)
    description = models.CharField(verbose_name=_('description'), max_length=255, blank=True)
    achieve_by = models.DateField(verbose_name=_('achieve by'), null=True, blank=True)
    date_created = models.DateField(auto_now_add=True, verbose_name=_('date created'))
    is_achieved = models.BooleanField(verbose_name=_('is achieved'), default=False, blank=True)
