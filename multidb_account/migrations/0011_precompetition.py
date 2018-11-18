# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-08-22 18:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('multidb_account', '0010_goal'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreCompetition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('goal', models.CharField(blank=True, max_length=255, verbose_name='title')),
                ('date', models.DateField(verbose_name='date')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='date created')),
                ('stress', models.PositiveSmallIntegerField(verbose_name='stress')),
                ('fatigue', models.PositiveSmallIntegerField(verbose_name='fatigue')),
                ('hydration', models.PositiveSmallIntegerField(verbose_name='hydration')),
                ('injury', models.PositiveSmallIntegerField(verbose_name='injury')),
                ('weekly_load', models.PositiveSmallIntegerField(verbose_name='weekly load')),
                ('athlete', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='multidb_account.AthleteUser', verbose_name='athlete')),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='multidb_account.Team', verbose_name='team')),
            ],
        ),
    ]
