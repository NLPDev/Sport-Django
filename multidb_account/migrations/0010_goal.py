# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-08-22 20:37
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('multidb_account', '0009_auto_20170817_1422'),
    ]

    operations = [
        migrations.CreateModel(
            name='Goal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(blank=True, max_length=255, verbose_name='description')),
                ('achieve_by', models.DateField(blank=True, null=True, verbose_name='achieve by')),
                ('date_created', models.DateField(auto_now_add=True, verbose_name='date created')),
                ('is_achieved', models.BooleanField(default=False, verbose_name='is achieved')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
        ),
    ]
