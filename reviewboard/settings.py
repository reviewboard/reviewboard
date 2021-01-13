# Django settings for reviewboard project.

from __future__ import unicode_literals

import os
import re

import django
import djblets
from django.core.urlresolvers import reverse
from djblets.pipeline.settings import (DEFAULT_PIPELINE_COMPILERS,
                                       build_pipeline_settings)

from reviewboard.dependencies import (dependency_error,
                                      fail_if_missing_dependencies)
from reviewboard.staticbundles import PIPELINE_STYLESHEETS, PIPELINE_JAVASCRIPT


# Can't import django.utils.translation yet
def _(s):
    return s


#: The name of the product.
#:
#: This should not be changed.
PRODUCT_NAME = 'Review Board'

DEBUG = True

ADMINS = (
    ('Example Admin', 'admin@example.com'),
)

MANAGERS = ADMINS

# Time zone support. If enabled, Django stores date and time information as
# UTC in the database, uses time zone-aware datetime objects, and translates
# them to the user's time zone in templates and forms.
USE_TZ = True

# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# When USE_TZ is enabled, this is used as the default time zone for datetime
# objects
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

# This should match the ID of the Site object in the database.  This is used to
# figure out URLs to stick in e-mails and related pages.
SITE_ID = 1

# The prefix for e-mail subjects sent to administrators.
EMAIL_SUBJECT_PREFIX = "[Review Board] "

# Default name of the service used in From e-mail when not spoofing.
#
# This should generally not be overridden unless one needs to thoroughly
# distinguish between two different Review Board servers AND DMARC is causing
# issues for e-mails.
EMAIL_DEFAULT_SENDER_SERVICE_NAME = 'Review Board'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

MIDDLEWARE_CLASSES = [
    # Keep these first, in order
    'django.middleware.gzip.GZipMiddleware',
    'reviewboard.admin.middleware.InitReviewBoardMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    # These must go before anything that deals with settings.
    'djblets.siteconfig.middleware.SettingsMiddleware',
    'reviewboard.admin.middleware.LoadSettingsMiddleware',

    'djblets.extensions.middleware.ExtensionsMiddleware',
    'djblets.integrations.middleware.IntegrationsMiddleware',
    'djblets.log.middleware.LoggingMiddleware',
    'reviewboard.accounts.middleware.TimezoneMiddleware',
    'reviewboard.accounts.middleware.UpdateLastLoginMiddleware',
    'reviewboard.admin.middleware.CheckUpdatesRequiredMiddleware',
    'reviewboard.accounts.middleware.X509AuthMiddleware',
    'reviewboard.site.middleware.LocalSiteMiddleware',

    # Keep this second to last so that everything is initialized before
    # middleware from extensions are run.
    'djblets.extensions.middleware.ExtensionsMiddlewareRunner',

    # Keep this last so we can set the details for an exception as soon as
    # possible.
    'reviewboard.admin.middleware.ExtraExceptionInfoMiddleware',
]
RB_EXTRA_MIDDLEWARE_CLASSES = []

SITE_ROOT_URLCONF = 'reviewboard.urls'
ROOT_URLCONF = 'djblets.urls.root'

REVIEWBOARD_ROOT = os.path.abspath(os.path.split(__file__)[0])

# where is the site on your server ? - add the trailing slash.
SITE_ROOT = '/'

STATICFILES_DIRS = (
    ('lib', os.path.join(REVIEWBOARD_ROOT, 'static', 'lib')),
    ('rb', os.path.join(REVIEWBOARD_ROOT, 'static', 'rb')),
    ('djblets', os.path.join(os.path.dirname(djblets.__file__),
                             'static', 'djblets')),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'djblets.extensions.staticfiles.ExtensionFinder',
    'pipeline.finders.PipelineFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

RB_BUILTIN_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'djblets',
    'djblets.avatars',
    'djblets.configforms',
    'djblets.datagrid',
    'djblets.extensions',
    'djblets.features',
    'djblets.feedview',
    'djblets.forms',
    'djblets.gravatars',
    'djblets.integrations',
    'djblets.log',
    'djblets.pipeline',
    'djblets.privacy',
    'djblets.recaptcha',
    'djblets.siteconfig',
    'djblets.util',
    'haystack',
    'oauth2_provider',
    'pipeline',  # Must be after djblets.pipeline
    'reviewboard',
    'reviewboard.accounts',
    'reviewboard.admin',
    'reviewboard.attachments',
    'reviewboard.avatars',
    'reviewboard.changedescs',
    'reviewboard.diffviewer',
    'reviewboard.extensions',
    'reviewboard.hostingsvcs',
    'reviewboard.integrations',
    'reviewboard.notifications',
    'reviewboard.oauth',
    'reviewboard.reviews',
    'reviewboard.scmtools',
    'reviewboard.site',
    'reviewboard.webapi',
]

# If installed, add django_reset to INSTALLED_APPS. This is used for the
# 'manage.py reset' command, which is very useful during development.
try:
    import django_reset
    RB_BUILTIN_APPS.append('django_reset')
except ImportError:
    pass

RB_EXTRA_APPS = []

WEB_API_ENCODERS = (
    'djblets.webapi.encoders.ResourceAPIEncoder',
)

# The backends that are used to authenticate requests against the web API.
WEB_API_AUTH_BACKENDS = (
    'reviewboard.webapi.auth_backends.WebAPIBasicAuthBackend',
    'djblets.webapi.auth.backends.api_tokens.WebAPITokenAuthBackend',
)

WEB_API_SCOPE_DICT_CLASS = (
    'djblets.webapi.oauth2_scopes.ExtensionEnabledWebAPIScopeDictionary')

WEB_API_ROOT_RESOURCE = 'reviewboard.webapi.resources.root.root_resource'

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# A list of supported password hashers. This contains some old hashers we no
# longer want to use to generate passwords, but are needed for legacy servers.
#
# This is current as of Django 1.11.
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.UnsaltedSHA1PasswordHasher',
    'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
    'django.contrib.auth.hashers.CryptPasswordHasher',
)

# Set up a default cache backend. This will mostly be useful for
# local development, as sites will override this.
#
# Later on, we'll swap this 'default' out for the forwarding cache,
# and set up 'default' as the cache being forwarded to.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'reviewboard',
    },
}

LOGGING_NAME = "reviewboard"
LOGGING_REQUEST_FORMAT = "%(_local_site_name)s - %(user)s - %(path)s"
LOGGING_BLACKLIST = [
    'django.db.backends',
    'MARKDOWN',
    'PIL.Image',
]

AUTH_PROFILE_MODULE = "accounts.Profile"

# Default expiration time for the cache.  Note that this has no effect unless
# CACHE_BACKEND is specified in settings_local.py
CACHE_EXPIRATION_TIME = 60 * 60 * 24 * 30  # 1 month

# Custom test runner, which uses nose to find tests and execute them.  This
# gives us a somewhat more comprehensive test execution than django's built-in
# runner, as well as some special features like a code coverage report.
TEST_RUNNER = 'reviewboard.test.RBTestRunner'

RUNNING_TEST = (os.environ.get(str('RB_RUNNING_TESTS')) == str('1'))


LOCAL_ROOT = None
PRODUCTION = True

# Default ALLOWED_HOSTS to allow everything. This should be overridden in
# settings_local.py
ALLOWED_HOSTS = ['*']

# Disable specific Django system check warnings:
#
# fields.W342: Setting unique=True on a ForeignKey has the same effect as using
#              a OneToOneField.
SILENCED_SYSTEM_CHECKS = [
    'fields.W342',
]

# Cookie settings
LANGUAGE_COOKIE_NAME = "rblanguage"
SESSION_COOKIE_NAME = "rbsessionid"
SESSION_COOKIE_AGE = 365 * 24 * 60 * 60  # 1 year

# Default support settings
SUPPORT_URL_BASE = 'https://www.beanbaginc.com/support/reviewboard/'
DEFAULT_SUPPORT_URL = SUPPORT_URL_BASE + '?support-data=%(support_data)s'
REGISTER_SUPPORT_URL = (SUPPORT_URL_BASE +
                        'register/?support-data=%(support_data)s')

# Regular expression and flags used to match review request IDs in commit
# messages for hosting service webhooks. These can be overriden in
# settings_local.py.
HOSTINGSVCS_HOOK_REGEX = (r'(?:Reviewed at %(server_url)sr/|Review request #)'
                          r'(?P<id>\d+)')
HOSTINGSVCS_HOOK_REGEX_FLAGS = re.IGNORECASE


# The SVN backends to attempt to load, in order. This is useful if more than
# one type of backend is installed on a server, and you need to force usage
# of a specific one.
SVNTOOL_BACKENDS = [
    'reviewboard.scmtools.svn.pysvn',
    'reviewboard.scmtools.svn.subvertpy',
]

# Gravatar configuration.
GRAVATAR_DEFAULT = 'mm'


# A list of extensions that will be enabled by default when first loading the
# extension registration. These won't be re-enabled automatically if disabled.
EXTENSIONS_ENABLED_BY_DEFAULT = [
    'rbintegrations.extension.RBIntegrationsExtension',
]

DJBLETS_EXTENSIONS_BROWSE_URL = 'https://www.reviewboard.org/store/'


# Load local settings.  This can override anything in here, but at the very
# least it needs to define database connectivity.
try:
    import settings_local
    from settings_local import *
except ImportError as exc:
    dependency_error('Unable to import settings_local.py: %s' % exc)


SESSION_COOKIE_PATH = SITE_ROOT

INSTALLED_APPS = RB_BUILTIN_APPS + RB_EXTRA_APPS + ['django_evolution']
MIDDLEWARE_CLASSES += RB_EXTRA_MIDDLEWARE_CLASSES


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(REVIEWBOARD_ROOT, 'templates'),
        ],
        'OPTIONS': {
            'builtins': [
                'reviewboard.site.templatetags.localsite',
            ],
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'djblets.cache.context_processors.ajax_serial',
                'djblets.cache.context_processors.media_serial',
                'djblets.siteconfig.context_processors.siteconfig',
                'djblets.siteconfig.context_processors.settings_vars',
                'djblets.urls.context_processors.site_root',
                'reviewboard.accounts.context_processors.auth_backends',
                'reviewboard.accounts.context_processors.profile',
                'reviewboard.admin.context_processors.read_only',
                'reviewboard.admin.context_processors.version',
                'reviewboard.site.context_processors.localsite',
            ],
            'debug': DEBUG,
            'loaders': [
                (
                    'djblets.template.loaders.conditional_cached.Loader',
                    (
                        'django.template.loaders.filesystem.Loader',
                        'djblets.template.loaders.namespaced_app_dirs.Loader',
                        'djblets.extensions.loaders.Loader',
                    )
                ),
            ],
        },
    },
]


if not LOCAL_ROOT:
    local_dir = os.path.dirname(settings_local.__file__)

    if os.path.exists(os.path.join(local_dir, 'reviewboard')):
        # reviewboard/ is in the same directory as settings_local.py.
        # This is probably a Git checkout.
        LOCAL_ROOT = os.path.join(local_dir, 'reviewboard')
        PRODUCTION = False
    else:
        # This is likely a site install. Get the parent directory.
        LOCAL_ROOT = os.path.dirname(local_dir)

if PRODUCTION:
    SITE_DATA_DIR = os.path.join(LOCAL_ROOT, 'data')
else:
    SITE_DATA_DIR = os.path.dirname(LOCAL_ROOT)

HTDOCS_ROOT = os.path.join(LOCAL_ROOT, 'htdocs')
STATIC_ROOT = os.path.join(HTDOCS_ROOT, 'static')
MEDIA_ROOT = os.path.join(HTDOCS_ROOT, 'media')
ADMIN_MEDIA_ROOT = STATIC_ROOT + 'admin/'

# XXX This is deprecated, but kept around for compatibility, in case any
#     old extensions reference it. We'll want to deprecate it.
EXTENSIONS_STATIC_ROOT = os.path.join(MEDIA_ROOT, 'ext')

# Set up our forwarding search backend for Haystack. This loads the configured
# Review Board search backend.
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'reviewboard.search.haystack_backend.ForwardingSearchEngine',
    },
}

HAYSTACK_SIGNAL_PROCESSOR = \
    'reviewboard.search.signal_processor.SignalProcessor'


# Custom Django Evolutions for modules we use.
CUSTOM_EVOLUTIONS = {
    'oauth2_provider': 'reviewboard.admin.custom_evolutions.oauth2_provider',
}

# Make sure that we have a staticfiles cache set up for media generation.
# By default, we want to store this in local memory and not memcached or
# some other backend, since that will cause stale media problems.
if 'staticfiles' not in CACHES:
    CACHES['staticfiles'] = {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'staticfiles-filehashes',
    }


# Set up a ForwardingCacheBackend, and forward to the user's specified cache.
# We're swapping this around so that the 'default' is forced to be the
# the forwarding backend, and the former 'default' is what's being forwarded
# to. This is necessary because the settings_local.py will likely specify
# a default.
CACHES['forwarded_backend'] = CACHES['default']
CACHES['default'] = {
    'BACKEND': 'djblets.cache.forwarding_backend.ForwardingCacheBackend',
    'LOCATION': 'forwarded_backend',
}


# URL prefix for media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
#
# Examples: "http://foo.com/media/", "/media/".
STATIC_DIRECTORY = 'static/'
STATIC_URL = getattr(settings_local, 'STATIC_URL',
                     SITE_ROOT + STATIC_DIRECTORY)

MEDIA_DIRECTORY = 'media/'
MEDIA_URL = getattr(settings_local, 'MEDIA_URL', SITE_ROOT + MEDIA_DIRECTORY)


# Base these on the user's SITE_ROOT.
LOGIN_URL = SITE_ROOT + 'account/login/'
LOGIN_REDIRECT_URL = SITE_ROOT + 'dashboard/'


# Static media setup
if RUNNING_TEST:
    _pipeline_compilers = []
else:
    _pipeline_compilers = DEFAULT_PIPELINE_COMPILERS

NODE_PATH = os.path.abspath(os.path.join(REVIEWBOARD_ROOT, '..',
                                         'node_modules'))


PIPELINE = build_pipeline_settings(
    # On production (site-installed) builds, we always want to use the
    # pre-compiled versions. We want this regardless of the DEBUG setting
    # (since they may turn DEBUG on in order to get better error output).
    pipeline_enabled=(PRODUCTION or not DEBUG or
                      os.getenv('FORCE_BUILD_MEDIA', '')),
    node_modules_path=NODE_PATH,
    static_root=STATIC_ROOT,
    compilers=_pipeline_compilers,
    validate_paths=not PRODUCTION,
    javascript_bundles=PIPELINE_JAVASCRIPT,
    stylesheet_bundles=PIPELINE_STYLESHEETS,
    less_extra_args=[
        # This is just here for backwards-compatibility with any stylesheets
        # that still have this. It's no longer necessary because compilation
        # happens on the back-end instead of in the browser.
        '--global-var=STATIC_ROOT=""',
    ])


# Packages to unit test
TEST_PACKAGES = ['reviewboard']

# URL Overrides
ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda u: reverse('user', kwargs={'username': u.username})
}

FEATURE_CHECKER = 'reviewboard.features.checkers.RBFeatureChecker'

OAUTH2_PROVIDER = {
    'APPLICATION_MODEL': 'oauth.Application',
    'DEFAULT_SCOPES': 'root:read',
    'SCOPES': {},
}


fail_if_missing_dependencies()
