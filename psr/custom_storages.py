# custom_storages.py
import os
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

class S3StaticStorage(S3Boto3Storage):
    location = settings.STATICFILES_LOCATION


class S3MediaStorage(S3Boto3Storage):
    location = settings.MEDIAFILES_LOCATION

   
