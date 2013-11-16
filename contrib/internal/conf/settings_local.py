from __future__ import unicode_literals

import os


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'build-media.db',
    }
}

LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          '..', '..', '..', 'reviewboard'))
PRODUCTION = False
DEBUG = False

SECRET_KEY = '1234'
