# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('multidb_account', '0019_auto_20170901_1844'),
    ]

    operations = [
        migrations.CreateModel(
            name='AthleteNote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('doctor', models.CharField(max_length=255, verbose_name='doctor')),
                ('note', models.TextField(verbose_name='note')),
                ('date_created', models.DateField(auto_now_add=True, verbose_name='date created')),
            ],
        ),
        migrations.CreateModel(
            name='CoachNote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('note', models.TextField(verbose_name='note')),
                ('date_created', models.DateField(auto_now_add=True, verbose_name='date created')),
                ('athlete', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='multidb_account.AthleteUser', verbose_name='athlete')),
            ],
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(max_length=512, upload_to='files/%Y/%m/%d/%H/%M/%S')),
                ('date_created', models.DateField(auto_now_add=True, verbose_name='date created')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=512, unique=True, verbose_name='url')),
            ],
        ),
        migrations.CreateModel(
            name='ReturnToPlayType',
            fields=[
                ('value', models.CharField(max_length=64, primary_key=True, serialize=False, verbose_name='value')),
            ],
        ),
        migrations.AddField(
            model_name='coachnote',
            name='files',
            field=models.ManyToManyField(to='multidb_account.File'),
        ),
        migrations.AddField(
            model_name='coachnote',
            name='links',
            field=models.ManyToManyField(to='multidb_account.Link'),
        ),
        migrations.AddField(
            model_name='coachnote',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='multidb_account.CoachUser', verbose_name='owner'),
        ),
        migrations.AddField(
            model_name='coachnote',
            name='return_to_play_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='multidb_account.ReturnToPlayType', verbose_name='return to play type'),
        ),
        migrations.AddField(
            model_name='coachnote',
            name='team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='multidb_account.Team', verbose_name='team'),
        ),
        migrations.AddField(
            model_name='athletenote',
            name='files',
            field=models.ManyToManyField(to='multidb_account.File'),
        ),
        migrations.AddField(
            model_name='athletenote',
            name='links',
            field=models.ManyToManyField(to='multidb_account.Link'),
        ),
        migrations.AddField(
            model_name='athletenote',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='multidb_account.AthleteUser', verbose_name='owner'),
        ),
        migrations.AddField(
            model_name='athletenote',
            name='return_to_play_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='multidb_account.ReturnToPlayType', verbose_name='return to play type'),
        ),
    ]
