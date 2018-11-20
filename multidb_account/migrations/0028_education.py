# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-10-18 14:35
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('multidb_account', '0027_auto_20171018_1410'),
    ]

    operations = [
        migrations.CreateModel(
            name='Education',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gpa', models.DecimalField(decimal_places=1, max_digits=2, verbose_name='gpa')),
                ('school', models.CharField(blank=True, max_length=255, verbose_name='school')),
                ('current', models.BooleanField(default=False, verbose_name='current')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
        ),
    ]