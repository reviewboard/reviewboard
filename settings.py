# Django settings for reviewboard project.

import os
import sys


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
USE_I18N = True

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'djblets.util.context_processors.settingsVars',
    'djblets.util.context_processors.siteRoot',
)

SITE_ROOT_URLCONF = 'reviewboard.urls'
ROOT_URLCONF = 'djblets.util.rooturl'

REVIEWBOARD_ROOT = os.path.abspath(os.path.split(__file__)[0])

HTDOCS_ROOT = os.path.join(REVIEWBOARD_ROOT, 'htdocs')
MEDIA_ROOT = os.path.join(HTDOCS_ROOT, 'media')

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
    'djblets.util',
    'djblets.webapi',
    'reviewboard.accounts',
    'reviewboard.admin',
    'reviewboard.diffviewer',
    'reviewboard.iphone',
    'reviewboard.reports',
    'reviewboard.reviews',
    'reviewboard.scmtools',
    'reviewboard.webapi',
    'django_evolution', # Must be last
)

WEB_API_ENCODERS = (
    'djblets.webapi.core.BasicAPIEncoder',
    'reviewboard.webapi.json.ReviewBoardAPIEncoder',
)

# Whether to use django's built-in system for users.  This turns on certain
# features like the registration page and profile editing.  If you're tying
# reviewboard in to an existing authentication environment (such as NIS),
# this data will come in from outside.
BUILTIN_AUTH = True
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

# List of file patterns that will show whitespace-only changes. The
# default behavior for diffs is to hide lines showing only leading
# whitespace changes.
#
# For example:
#
#    DIFF_INCLUDE_SPACE_PATTERNS = ["*.py", "*.txt"]
#
DIFF_INCLUDE_SPACE_PATTERNS = []

# When enabled, this will send e-mails for all review requests and comments
# out to the e-mail addresses defined for the group.
SEND_REVIEW_MAIL = False

# Enable syntax highlighting in the diff viewer
DIFF_SYNTAX_HIGHLIGHTING = False

# Access method used for the site, used in e-mails.  Override this in
# settings_local.py if you choose to use https instead of http.
DOMAIN_METHOD = "http"

# Require a login for accessing any part of the site. If False, review
# requests, diffs, lists of review requests, etc. will be accessible without
# a login.
REQUIRE_SITEWIDE_LOGIN = False

# Enable search. See the comment in settings_local.py for more information on
# what's required to get this working.
ENABLE_SEARCH = False
SEARCH_INDEX = os.path.join(REVIEWBOARD_ROOT, 'search-index')

# The number of files to display per page in the diff viewer
DIFFVIEWER_PAGINATE_BY = 20

# The number of extra files required before adding another page
DIFFVIEWER_PAGINATE_ORPHANS = 10

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

if os.path.split(os.path.dirname(__file__))[1] != 'reviewboard':
    dependency_error('The directory containing manage.py must be named "reviewboard"')

# Load local settings.  This can override anything in here, but at the very
# least it needs to define database connectivity.
try:
    import settings_local
    from settings_local import *
except ImportError:
    dependency_error('Unable to read settings_local.py.')

TEMPLATE_DEBUG = DEBUG

# URL prefix for media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
#
# Examples: "http://foo.com/media/", "/media/".
MEDIA_URL = getattr(settings_local, 'MEDIA_URL', SITE_ROOT + 'media/')


# Base these on the user's SITE_ROOT.
LOGIN_URL = SITE_ROOT + 'account/login/'
ADMIN_MEDIA_PREFIX = MEDIA_URL + 'admin/'

# Cookie settings
SESSION_COOKIE_NAME = "rbsessionid"
SESSION_COOKIE_AGE = 365 * 24 * 24 * 60 # 1 year
SESSION_COOKIE_PATH = SITE_ROOT
