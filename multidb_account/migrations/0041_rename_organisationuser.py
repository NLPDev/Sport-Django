# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-03-08 16:02
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('multidb_account', '0040_increase_user_country_length'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='OrganisationUser',
            table='multidb_account_organisation',
        ),
        migrations.RenameModel(
            old_name='OrganisationUser',
            new_name='Organisation',
        ),
    ]
