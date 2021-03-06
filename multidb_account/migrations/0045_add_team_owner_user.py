# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-29 11:52
from __future__ import unicode_literals

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('multidb_account', '0044_add_id_organisation'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='organisation',
            options={'verbose_name_plural': 'organisations'},
        ),
        migrations.AddField(
            model_name='team',
            name='owner_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='team',
            name='organisation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='teams', to='multidb_account.Organisation',
                                    verbose_name='organisation'),
        ),
    ]
