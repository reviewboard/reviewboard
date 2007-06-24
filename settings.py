# Django settings for reviewboard project.

import os
import sys

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Example Joe', 'admin@example.com')
)

MANAGERS = ADMINS

# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/current/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
TIME_ZONE = 'US/Pacific'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'reviewboard.urls'

REVIEWBOARD_ROOT = os.path.abspath(os.path.split(__file__)[0])

TEMPLATE_ROOT = '/var/www/reviewboard'
HTDOCS_ROOT = os.path.join(REVIEWBOARD_ROOT, 'htdocs')
MEDIA_ROOT = HTDOCS_ROOT
MEDIA_URL = '/'

TEMPLATE_DIRS = (
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(REVIEWBOARD_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.sessions',
    'djblets.util',
    'reviewboard.accounts',
    'reviewboard.diffviewer',
    'reviewboard.reviews',
    'reviewboard.scmtools',
    'reviewboard.utils',
)

# Whether to use django's built-in system for users.  This turns on certain
# features like the registration page and profile editing.  If you're tying
# reviewboard in to an existing authentication environment (such as NIS),
# this data will come in from outside.
BUILTIN_AUTH = True
LOGIN_URL = '/account/login'
AUTH_PROFILE_MODULE = "accounts.Profile"

# Default repository path to use for the source code.
DEFAULT_REPOSITORY_PATH = None

# Default expiration time for the cache.  Note that this has no effect unless
# CACHE_BACKEND is specified in settings_local.py
CACHE_EXPIRATION_TIME = 60 * 60 * 24 * 30 # 1 month

# Custom test runner, which uses nose to find tests and execute them.  This
# gives us a somewhat more comprehensive test execution than django's built-in
# runner, as well as some special features like a code coverage report.
TEST_RUNNER = 'reviewboard.test.runner'

# Default diff settings
DIFF_CONTEXT_NUM_LINES = 5
DIFF_CONTEXT_COLLAPSE_THRESHOLD = 2 * DIFF_CONTEXT_NUM_LINES + 3

# When enabled, this will send e-mails for all review requests and comments
# out to the e-mail addresses defined for the group.
SEND_REVIEW_MAIL = False

# Access method used for the site, used in e-mails.  Override this in
# settings_local.py if you choose to use https instead of http.
DOMAIN_METHOD = "http"

# Dependency checker functionality.  Gives our users nice errors when they start
# out, instead of encountering them later on.  Most of the magic for this
# happens in manage.py, not here.
install_help = '''
Please see http://code.google.com/p/reviewboard/wiki/GettingStarted
for help setting up Review Board.
'''
def dependency_error(string):
    sys.stderr.write('%s\n' % string)
    sys.stderr.write(install_help)
    sys.exit(1)

# Load local settings.  This can override anything in here, but at the very
# least it needs to define database connectivity.
try:
    from settings_local import *
except ImportError:
    dependency_error('Unable to read settings_local.py.')
