# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-09-28 18:21
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('multidb_account', '0023_tweak_notes'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='achievement',
            name='location',
        ),
    ]
