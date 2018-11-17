# Django dev settings for psr project.

from .common import *

# Specify here which localized databases are active. Users will be authenticated against databases in the given order
# always us the country ISO 3166 code
LOCALIZED_DATABASES = [
    'ca',
    'us',
]

# Add a new entrie for any other additionnal country
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'psr_dev',
        'USER': 'psr_dev',
        'PASSWORD': 'psr_dev',
        'HOST': 'localhost',
        'PORT': '5432',
    },
    'ca': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'psr_ca_dev',
        'USER': 'psr_ca_dev',
        'PASSWORD': 'psr_ca_dev',
        'HOST': 'localhost',
        'PORT': '5432',
    },
    'us': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'psr_us_dev',
        'USER': 'psr_us_dev',
        'PASSWORD': 'psr_us_dev',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(BASE_DIR, '../media/')

#STRIPE: payment gateway
#STRIPE_PUBLISHABLE_KEY = 'pk_test_OAemI8e8whcyl9AvsqNxFY3P'
# STRIPE_SECRET_KEY = 'sk_test_fjQVaAS1yfSHlrjRAxftjLS0'

DISABLE_EXPIRED_CUSTOMERS_TOKEN = os.environ.get('PSR_APP_USER_LOGIN_PATH', 'test token')

# import local settings
try:
    from .local_settings import *
except ImportError:
    pass
