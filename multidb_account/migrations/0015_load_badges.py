# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-08-28 20:37
from __future__ import unicode_literals

import os

from django.core.files import File
from django.db import migrations

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))


def load_badges(apps, schema_editor):
    badges_dir = os.path.join(CURRENT_PATH, '..', 'static', 'multidb_account', 'images', 'badges')

    Badge = apps.get_model('multidb_account', 'Badge')

    for badge_file_name in os.listdir(badges_dir):
        with open(os.path.join(badges_dir, badge_file_name), 'rb') as badge_img_fl:
            badge = Badge.objects.using(schema_editor.connection.alias).create()
            badge.image_url.save(badge_file_name, File(badge_img_fl), save=True)


def reverse_func(apps, schema_editor):
    del apps, schema_editor


class Migration(migrations.Migration):
    dependencies = [
        ('multidb_account', '0014_badges_achievements'),
    ]

    operations = [
        migrations.RunPython(load_badges, reverse_func),
    ]
