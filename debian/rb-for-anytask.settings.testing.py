# -*- coding: utf-8 -*-
from default_settings import *

DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'festival',                      # Or path to database file if using sqlite3.
        'USER': 'festival',                      # Not used with sqlite3.
        'PASSWORD': 'festivalp',                  # Not used with sqlite3.
        'HOST': 'spec-dbm.test.spec.yandex.net',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

LOCALE_PATHS = (
    '/usr/lib/yandex/yandex-festivals/locale',
)

MEDIA_ROOT = '/usr/lib/yandex/yandex-festivals/festival/media/'
MEDIA_URL = '/fest/media/md/'

WWW_PATH = '/usr/lib/yandex/yandex-festivals/festival_front/www'
S_INDEX = 'http://seal001.search.yandex.net:17311'
WIZARD_URL = 'http://reqwizard.yandex.net:8891/'
STATIC_URL_FRONT = '/fest/media/static/'
LOGGING = {}
LOGGING_CONFIG = ''

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    '/usr/lib/yandex/yandex-festivals/templates',
)
