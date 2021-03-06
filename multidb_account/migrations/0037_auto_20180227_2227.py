# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-02-27 22:27
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.utils.timezone
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('multidb_account', '0036_private_assessments'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='assessment',
            options={'ordering': ['name'], 'verbose_name': 'Metric', 'verbose_name_plural': 'Metrics'},
        ),
        migrations.AlterModelOptions(
            name='assessmentformat',
            options={'verbose_name': 'Metric format', 'verbose_name_plural': 'Metric formats'},
        ),
        migrations.AddField(
            model_name='promocode',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='promocode',
            name='end_date',
            field=models.DateTimeField(default=datetime.datetime(2018, 2, 27, 22, 27, 46, 193556, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='promocode',
            name='start_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='assessmentformat',
            name='description',
            field=models.CharField(blank=True, max_length=255, verbose_name='format description'),
        ),
        migrations.AlterField(
            model_name='assessmentformat',
            name='unit',
            field=models.CharField(max_length=50, verbose_name='format unit'),
        ),
        migrations.AlterField(
            model_name='assessmentformat',
            name='validation_regex',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='metric value validation regex'),
        ),
        migrations.AlterField(
            model_name='invite',
            name='recipient_type',
            field=models.CharField(choices=[('coach', 'Coach'), ('athlete', 'Athlete'), ('organisation', 'Organisation')], max_length=50, null=True, verbose_name='recipient type'),
        ),
    ]
