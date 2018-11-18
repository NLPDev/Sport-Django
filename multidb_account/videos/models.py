from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from multidb_account.choices import VIDEO_TYPES, VIDEO_VIMEO, VIDEO_YOUTUBE


class Video(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), on_delete=models.CASCADE)
    video_type = models.CharField(max_length=7, choices=VIDEO_TYPES, verbose_name=_('video type'))
    video_id = models.CharField(max_length=20, verbose_name=_('video id'))
    video_name = models.CharField(max_length=512, verbose_name=_('video name'))
    date_added = models.DateTimeField(auto_now_add=True, verbose_name=_('date added'))
