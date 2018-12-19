"""
Django settings for psr project.

Generated by 'django-admin startproject' using Django 1.11.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import datetime

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANAGE_PY_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'ui@+$uk7y2phvbf0id$-%dcp%y6zmka7l-88y+!508bs0-%jfy'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

CORS_ORIGIN_ALLOW_ALL = True

# Application definition
DJANGO_APPS = [
    # django-autocomplete-light is a 3rd party app that must be installed before django.contrib.admin
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'corsheaders',
    'storages',
    'rest_framework',
    'imagekit',  # Image processing
    'django_extensions',
]

# Apps specific for this project go here.
LOCAL_APPS = [
    'multidb_account',
    'rest_api',
    'payment_gateway',
    'sport_engine',
]

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'multidb_account.middleware.MultiDbMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'psr.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(MANAGE_PY_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'psr.wsgi.application'


AUTHENTICATION_BACKENDS = [
    'multidb_account.multidb_auth_backend.MultidbAuthBackend',
]

AUTH_USER_MODEL = 'multidb_account.BaseCustomUser'

LOGIN_REDIRECT_URL = '/'

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_api.authentication.PsrJSONWebTokenAuthentication',

    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.MultiPartRenderer',  # For image uploading
    ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

#  JWT token configuration
JWT_AUTH = {
    'JWT_PAYLOAD_HANDLER': 'rest_api.utils.custom_jwt_payload_handler',
    'JWT_EXPIRATION_DELTA': datetime.timedelta(hours=24),
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(hours=24),
    'JWT_ALLOW_REFRESH': True
}

# 30min = 1800 seconds
PASSWORD_RESET_TOKEN_EXPIRES = int(1800)
# 7 days = 604800 seconds
USER_INVITE_TOKEN_EXPIRES = int(604800)
# 24 hours = 86400 seconds
USER_INVITE_TIMEOUT = int(86400)
# 30 days = 2592000 seconds
ATHLETE_COACH_ASSESSMENT_TIMEOUT = int(2592000)

# EMAIL TEMPLATES
RESET_PASSWORD_EMAIL_TEMPLATE = 'multidb_account/reset_password'
RESET_PASSWORD_CONFIRM_EMAIL_TEMPLATE = 'multidb_account/reset_password_confirm'
CONFIRM_ACCOUNT_EMAIL_TEMPLATE = 'multidb_account/confirm_account'
CONFIRM_ACCOUNT_CONFIRM_TEMPLATE = 'multidb_account/confirm_account_confirm'
USER_INVITE_EMAIL_TEMPLATE = 'multidb_account/user_invite'
WELCOME_EMAIL_TEMPLATE = 'multidb_account/welcome'
HELP_CENTER_NOTIFICATION_EMAIL_TEMPLATE = 'help_center/notification'
HELP_CENTER_ORG_SUPPORT_NOTIFICATION_EMAIL_TEMPLATE = 'help_center/organisation_support_notification'

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en'

gettext = lambda x: x
LANGUAGES = (
    ('en', gettext('English')),
    ('fr', gettext('French')),
)

USE_I18N = True
USE_L10N = True
TIME_ZONE = 'UTC'
USE_TZ = True

# A list of emails to notify on every help-center-report form submission
HELP_CENTER_FORM_EMAILS = []
# A list of emails to notify on every organisation-support form submission
HELP_CENTER_ORG_SUPPORT_FORM_EMAILS = []
