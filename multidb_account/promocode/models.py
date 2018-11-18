from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone


class Promocode(models.Model):
    code = models.CharField(verbose_name=_('code'), max_length=32, unique=True)
    discount = models.PositiveSmallIntegerField(verbose_name=_('discount'))
    name = models.CharField(verbose_name=_('name'), max_length=255)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return 'code={}'.format(self.code)
