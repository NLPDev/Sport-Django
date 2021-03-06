# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-03-18 18:15
from __future__ import unicode_literals

from django.db import migrations


# noinspection PyPep8Naming
def forwards_func(apps, schema_editor):
    Organisation = apps.get_model('multidb_account', 'Organisation')
    db_alias = schema_editor.connection.alias

    for org in Organisation.objects.using(db_alias):
        org.login_users.add(org.user)


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('multidb_account', '0042_organisation_login_users'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
