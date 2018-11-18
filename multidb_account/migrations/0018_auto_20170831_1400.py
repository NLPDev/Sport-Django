# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-08-31 14:00
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('multidb_account', '0017_auto_20170831_1345'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='achievement',
            name='datetime',
        ),
        migrations.AddField(
            model_name='achievement',
            name='date',
            field=models.DateField(default=datetime.datetime(2017, 8, 31, 14, 0, 19, 768487, tzinfo=utc), verbose_name='date'),
            preserve_default=False,
        ),
    ]
