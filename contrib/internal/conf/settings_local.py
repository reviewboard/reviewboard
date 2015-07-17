from __future__ import unicode_literals

import os

import djblets


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

PIPELINE_LESS_ARGUMENTS = ' '.join([
    '--include-path=%s' % os.path.join(os.path.dirname(djblets.__file__),
                                       'static'),
    '--global-var="STATIC_ROOT=\\"\\""',
    '--global-var="DEBUG=false"',
])
