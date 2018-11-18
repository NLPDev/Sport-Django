from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class Education(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), on_delete=models.CASCADE)
    gpa = models.DecimalField(verbose_name=_('gpa'), max_digits=2, decimal_places=1)
    school = models.CharField(verbose_name=_('school'), max_length=255, blank=True)
    current = models.BooleanField(verbose_name=_('current'), default=False, blank=True)
