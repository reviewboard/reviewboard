# Django settings for reviewboard project.

import os
import sys

# Can't import django.utils.translation yet
_ = lambda s: s


DEBUG = True

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

# This should match the ID of the Site object in the database.  This is used to
# figure out URLs to stick in e-mails and related pages.
SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False
LANGUAGES = (
    ('en', _('English')),
    )

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware', # Keep this first.
    'django.middleware.common.CommonMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # These must go before anything that deals with settings.
    'djblets.siteconfig.middleware.SettingsMiddleware',
    'reviewboard.admin.middleware.LoadSettingsMiddleware',

    'djblets.log.middleware.LoggingMiddleware',
    'reviewboard.admin.middleware.CheckUpdatesRequiredMiddleware',
    'reviewboard.admin.middleware.X509AuthMiddleware',
    'reviewboard.site.middleware.LocalSiteMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'djblets.siteconfig.context_processors.siteconfig',
    'djblets.util.context_processors.settingsVars',
    'djblets.util.context_processors.siteRoot',
    'djblets.util.context_processors.ajaxSerial',
    'djblets.util.context_processors.mediaSerial',
    'reviewboard.accounts.context_processors.auth_backends',
    'reviewboard.admin.context_processors.version',
    'reviewboard.site.context_processors.localsite',
)

SITE_ROOT_URLCONF = 'reviewboard.urls'
ROOT_URLCONF = 'djblets.util.rooturl'

REVIEWBOARD_ROOT = os.path.abspath(os.path.split(__file__)[0])

# where is the site on your server ? - add the trailing slash.
SITE_ROOT = '/'

TEMPLATE_DIRS = (
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(REVIEWBOARD_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.markup',
    'django.contrib.sites',
    'django.contrib.sessions',
    'djblets.datagrid',
    'djblets.feedview',
    'djblets.gravatars',
    'djblets.log',
    'djblets.siteconfig',
    'djblets.util',
    'djblets.webapi',
    'reviewboard.accounts',
    'reviewboard.admin',
    'reviewboard.changedescs',
    'reviewboard.diffviewer',
    'reviewboard.notifications',
    'reviewboard.reports',
    'reviewboard.reviews',
    'reviewboard.scmtools',
    'reviewboard.site',
    'reviewboard.webapi',
    'django_evolution', # Must be last
)

WEB_API_ENCODERS = (
    'djblets.webapi.encoders.ResourceAPIEncoder',
)

LOGGING_NAME = "reviewboard"

AUTH_PROFILE_MODULE = "accounts.Profile"

# Default expiration time for the cache.  Note that this has no effect unless
# CACHE_BACKEND is specified in settings_local.py
CACHE_EXPIRATION_TIME = 60 * 60 * 24 * 30 # 1 month

# Custom test runner, which uses nose to find tests and execute them.  This
# gives us a somewhat more comprehensive test execution than django's built-in
# runner, as well as some special features like a code coverage report.
TEST_RUNNER = 'reviewboard.test.runner'

# Dependency checker functionality.  Gives our users nice errors when they start
# out, instead of encountering them later on.  Most of the magic for this
# happens in manage.py, not here.
install_help = '''
Please see http://www.reviewboard.org/docs/manual/dev/admin/
for help setting up Review Board.
'''
def dependency_error(string):
    sys.stderr.write('%s\n' % string)
    sys.stderr.write(install_help)
    sys.exit(1)

if os.path.split(os.path.dirname(__file__))[1] != 'reviewboard':
    dependency_error('The directory containing manage.py must be named "reviewboard"')

LOCAL_ROOT = None

# Load local settings.  This can override anything in here, but at the very
# least it needs to define database connectivity.
try:
    import settings_local
    from settings_local import *
except ImportError:
    dependency_error('Unable to read settings_local.py.')

TEMPLATE_DEBUG = DEBUG

if not LOCAL_ROOT:
    local_dir = os.path.dirname(settings_local.__file__)

    if os.path.exists(os.path.join(local_dir, 'reviewboard')):
        # reviewboard/ is in the same directory as settings_local.py.
        # This is probably a Git checkout.
        LOCAL_ROOT = os.path.join(local_dir, 'reviewboard')
    else:
        # This is likely a site install. Get the parent directory.
        LOCAL_ROOT = os.path.dirname(local_dir)

HTDOCS_ROOT = os.path.join(LOCAL_ROOT, 'htdocs')
MEDIA_ROOT = os.path.join(HTDOCS_ROOT, 'media')


# URL prefix for media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
#
# Examples: "http://foo.com/media/", "/media/".
MEDIA_URL = getattr(settings_local, 'MEDIA_URL', SITE_ROOT + 'media/')


# Base these on the user's SITE_ROOT.
LOGIN_URL = SITE_ROOT + 'account/login/'
ADMIN_MEDIA_PREFIX = MEDIA_URL + 'admin/'

# Cookie settings
LANGUAGE_COOKIE_NAME = "rblanguage"
SESSION_COOKIE_NAME = "rbsessionid"
SESSION_COOKIE_AGE = 365 * 24 * 60 * 60 # 1 year
SESSION_COOKIE_PATH = SITE_ROOT

# The list of directories that will be searched to generate a media serial.
MEDIA_SERIAL_DIRS = ["admin", "djblets", "rb"]

TEST_PACKAGES = ['reviewboard']
