# Django settings for reviewboard project.

import os
import sys

import djblets
from djblets.settings import (PIPELINE_JS as DJBLETS_PIPELINE_JS,
                              PIPELINE_CSS as DJBLETS_PIPELINE_CSS)
from django.core.urlresolvers import reverse


# Can't import django.utils.translation yet
_ = lambda s: s


DEBUG = True

ADMINS = (
    ('Example Joe', 'admin@example.com')
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

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
LANGUAGES = (
    ('en', _('English')),
    ('it', _('Italian')),
    ('zh-tw', _('Traditional Chinese')),
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
        'djblets.extensions.loaders.load_template_source',
    )),
)

MIDDLEWARE_CLASSES = [
    # Keep these first, in order
    'django.middleware.gzip.GZipMiddleware',
    'reviewboard.admin.middleware.InitReviewBoardMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    # These must go before anything that deals with settings.
    'djblets.siteconfig.middleware.SettingsMiddleware',
    'reviewboard.admin.middleware.LoadSettingsMiddleware',

    'djblets.extensions.middleware.ExtensionsMiddleware',
    'djblets.log.middleware.LoggingMiddleware',
    'reviewboard.accounts.middleware.TimezoneMiddleware',
    'reviewboard.admin.middleware.CheckUpdatesRequiredMiddleware',
    'reviewboard.admin.middleware.X509AuthMiddleware',
    'reviewboard.site.middleware.LocalSiteMiddleware',

    # Keep this last so that everything is initialized before middleware
    # from extensions are run.
    'djblets.extensions.middleware.ExtensionsMiddlewareRunner',
]
RB_EXTRA_MIDDLEWARE_CLASSES = []

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'djblets.siteconfig.context_processors.siteconfig',
    'djblets.util.context_processors.settingsVars',
    'djblets.util.context_processors.siteRoot',
    'djblets.util.context_processors.ajaxSerial',
    'djblets.util.context_processors.mediaSerial',
    'reviewboard.accounts.context_processors.auth_backends',
    'reviewboard.accounts.context_processors.profile',
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
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

RB_BUILTIN_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.markup',
    'django.contrib.sites',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'djblets.datagrid',
    'djblets.extensions',
    'djblets.feedview',
    'djblets.gravatars',
    'djblets.log',
    'djblets.pipeline',
    'djblets.siteconfig',
    'djblets.util',
    'djblets.webapi',
    'pipeline',  # Must be after djblets.pipeline
    'reviewboard',
    'reviewboard.accounts',
    'reviewboard.admin',
    'reviewboard.attachments',
    'reviewboard.changedescs',
    'reviewboard.diffviewer',
    'reviewboard.extensions',
    'reviewboard.hostingsvcs',
    'reviewboard.notifications',
    'reviewboard.reviews',
    'reviewboard.reviews.ui',
    'reviewboard.scmtools',
    'reviewboard.site',
    'reviewboard.ssh',
    'reviewboard.webapi',
]
RB_EXTRA_APPS = []

WEB_API_ENCODERS = (
    'djblets.webapi.encoders.ResourceAPIEncoder',
)

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# Set up a default cache backend. This will mostly be useful for
# local development, as sites will override this.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'reviewboard',
    },
}

LOGGING_NAME = "reviewboard"
LOGGING_REQUEST_FORMAT = "%(_local_site_name)s - %(user)s - %(path)s"

AUTH_PROFILE_MODULE = "accounts.Profile"

# Default expiration time for the cache.  Note that this has no effect unless
# CACHE_BACKEND is specified in settings_local.py
CACHE_EXPIRATION_TIME = 60 * 60 * 24 * 30  # 1 month

# Custom test runner, which uses nose to find tests and execute them.  This
# gives us a somewhat more comprehensive test execution than django's built-in
# runner, as well as some special features like a code coverage report.
TEST_RUNNER = 'reviewboard.test.RBTestRunner'

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
PRODUCTION = True

# Default ALLOWED_HOSTS to allow everything. This should be overridden in
# settings_local.py
ALLOWED_HOSTS = ['*']

# Cookie settings
LANGUAGE_COOKIE_NAME = "rblanguage"
SESSION_COOKIE_NAME = "rbsessionid"
SESSION_COOKIE_AGE = 365 * 24 * 60 * 60  # 1 year

# Default support settings
DEFAULT_SUPPORT_URL = 'http://www.beanbaginc.com/support/reviewboard/' \
                      '?support-data=%(support_data)s'


# Load local settings.  This can override anything in here, but at the very
# least it needs to define database connectivity.
try:
    import settings_local
    from settings_local import *
except ImportError, exc:
    dependency_error('Unable to import settings_local.py: %s' % exc)

SESSION_COOKIE_PATH = SITE_ROOT

INSTALLED_APPS = RB_BUILTIN_APPS + RB_EXTRA_APPS + ['django_evolution']
MIDDLEWARE_CLASSES += RB_EXTRA_MIDDLEWARE_CLASSES

TEMPLATE_DEBUG = DEBUG

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

HTDOCS_ROOT = os.path.join(LOCAL_ROOT, 'htdocs')
STATIC_ROOT = os.path.join(HTDOCS_ROOT, 'static')
MEDIA_ROOT = os.path.join(HTDOCS_ROOT, 'media')
EXTENSIONS_STATIC_ROOT = os.path.join(MEDIA_ROOT, 'ext')
ADMIN_MEDIA_ROOT = STATIC_ROOT + 'admin/'


# Make sure that we have a staticfiles cache set up for media generation.
# By default, we want to store this in local memory and not memcached or
# some other backend, since that will cause stale media problems.
if 'staticfiles' not in CACHES:
    CACHES['staticfiles'] = {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'staticfiles-filehashes',
    }


# URL prefix for media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
#
# Examples: "http://foo.com/media/", "/media/".
STATIC_DIRECTORY = 'static/'
STATIC_URL = getattr(settings_local, 'STATIC_URL', SITE_ROOT + STATIC_DIRECTORY)

MEDIA_DIRECTORY = 'media/'
MEDIA_URL = getattr(settings_local, 'MEDIA_URL', SITE_ROOT + MEDIA_DIRECTORY)


# Base these on the user's SITE_ROOT.
LOGIN_URL = SITE_ROOT + 'account/login/'

# Media compression
PIPELINE_JS = dict({
    '3rdparty': {
        'source_filenames': (
            'lib/js/flot/jquery.flot.min.js',
            'lib/js/flot/jquery.flot.pie.min.js',
            'lib/js/flot/jquery.flot.selection.min.js',
            'lib/js/flot/jquery.flot.time.min.js',
            'lib/js/underscore-1.4.4.min.js',
            'lib/js/backbone-1.0.0.min.js',
            'lib/js/jquery.cookie-1.3.1.js',
            'lib/js/jquery.form.js',
            'lib/js/jquery.timesince.js',
            'lib/js/moment-2.0.0.min.js',
            'lib/js/retina.js',
            'lib/js/ui.autocomplete.js',
            'lib/js/google-code-prettify/prettify.js',
            'lib/js/marked.js',
        ),
        'output_filename': 'lib/js/3rdparty.min.js',
    },
    'js-tests': {
        'source_filenames': (
            'lib/js/jasmine-1.3.1.js',
            'lib/js/jasmine-html-1.3.1.js',
            'rb/js/collections/tests/resourceCollectionTests.js',
            'rb/js/diffviewer/models/tests/diffFileModelTests.js',
            'rb/js/diffviewer/models/tests/diffReviewableModelTests.js',
            'rb/js/diffviewer/models/tests/diffRevisionModelTests.js',
            'rb/js/diffviewer/models/tests/paginationModelTests.js',
            'rb/js/diffviewer/views/tests/diffReviewableViewTests.js',
            'rb/js/models/tests/commentEditorModelTests.js',
            'rb/js/models/tests/reviewReplyEditorModelTests.js',
            'rb/js/models/tests/reviewRequestEditorModelTests.js',
            'rb/js/models/tests/userSessionModelTests.js',
            'rb/js/newReviewRequest/views/tests/branchesViewTests.js',
            'rb/js/newReviewRequest/views/tests/postCommitViewTests.js',
            'rb/js/newReviewRequest/views/tests/repositorySelectionViewTests.js',
            'rb/js/pages/models/tests/pageManagerModelTests.js',
            'rb/js/pages/views/tests/reviewablePageViewTests.js',
            'rb/js/resources/collections/tests/repositoryBranchesCollectionTests.js',
            'rb/js/resources/collections/tests/repositoryCommitsCollectionTests.js',
            'rb/js/resources/models/tests/baseCommentModelTests.js',
            'rb/js/resources/models/tests/baseCommentReplyModelTests.js',
            'rb/js/resources/models/tests/baseResourceModelTests.js',
            'rb/js/resources/models/tests/diffCommentModelTests.js',
            'rb/js/resources/models/tests/draftReviewModelTests.js',
            'rb/js/resources/models/tests/draftReviewRequestModelTests.js',
            'rb/js/resources/models/tests/fileAttachmentModelTests.js',
            'rb/js/resources/models/tests/fileAttachmentCommentModelTests.js',
            'rb/js/resources/models/tests/fileDiffModelTests.js',
            'rb/js/resources/models/tests/screenshotModelTests.js',
            'rb/js/resources/models/tests/screenshotCommentModelTests.js',
            'rb/js/resources/models/tests/repositoryBranchModelTests.js',
            'rb/js/resources/models/tests/repositoryCommitModelTests.js',
            'rb/js/resources/models/tests/reviewGroupModelTests.js',
            'rb/js/resources/models/tests/reviewModelTests.js',
            'rb/js/resources/models/tests/reviewReplyModelTests.js',
            'rb/js/resources/models/tests/reviewRequestModelTests.js',
            'rb/js/resources/models/tests/validateDiffModelTests.js',
            'rb/js/utils/tests/keyBindingUtilsTests.js',
            'rb/js/utils/tests/linkifyUtilsTests.js',
            'rb/js/utils/tests/propertyUtilsTests.js',
            'rb/js/views/tests/collectionViewTests.js',
            'rb/js/views/tests/commentDialogViewTests.js',
            'rb/js/views/tests/commentIssueBarViewTests.js',
            'rb/js/views/tests/diffFragmentQueueViewTests.js',
            'rb/js/views/tests/draftReviewBannerViewTests.js',
            'rb/js/views/tests/fileAttachmentThumbnailViewTests.js',
            'rb/js/views/tests/reviewBoxViewTests.js',
            'rb/js/views/tests/reviewBoxListViewTests.js',
            'rb/js/views/tests/reviewDialogViewTests.js',
            'rb/js/views/tests/reviewRequestEditorViewTests.js',
            'rb/js/views/tests/reviewReplyDraftBannerViewTests.js',
            'rb/js/views/tests/reviewReplyEditorViewTests.js',
            'rb/js/views/tests/screenshotThumbnailViewTests.js',
        ),
        'output_filename': 'rb/js/js-tests.min.js',
    },
    'common': {
        'source_filenames': (
            'rb/js/utils/backboneUtils.js',
            'rb/js/utils/compatUtils.js',
            'rb/js/utils/consoleUtils.js',
            'rb/js/utils/propertyUtils.js',
            'rb/js/utils/underscoreUtils.js',
            'rb/js/common.js',
            'rb/js/utils/apiErrors.js',
            'rb/js/utils/apiUtils.js',
            'rb/js/utils/linkifyUtils.js',
            'rb/js/utils/keyBindingUtils.js',
            'rb/js/collections/baseCollection.js',
            'rb/js/extensions/models/aliases.js',
            'rb/js/extensions/models/commentDialogHookModel.js',
            'rb/js/extensions/models/reviewDialogCommentHookModel.js',
            'rb/js/pages/models/pageManagerModel.js',
            'rb/js/resources/models/baseResourceModel.js',
            'rb/js/resources/models/draftResourceModelMixin.js',
            'rb/js/resources/models/draftReviewRequestModel.js',
            'rb/js/resources/models/reviewModel.js',
            'rb/js/resources/models/draftReviewModel.js',
            'rb/js/resources/models/baseCommentModel.js',
            'rb/js/resources/models/baseCommentReplyModel.js',
            'rb/js/resources/models/diffCommentModel.js',
            'rb/js/resources/models/diffCommentReplyModel.js',
            'rb/js/resources/models/diffModel.js',
            'rb/js/resources/models/fileAttachmentModel.js',
            'rb/js/resources/models/fileAttachmentCommentModel.js',
            'rb/js/resources/models/fileAttachmentCommentReplyModel.js',
            'rb/js/resources/models/fileDiffModel.js',
            'rb/js/resources/models/reviewGroupModel.js',
            'rb/js/resources/models/reviewReplyModel.js',
            'rb/js/resources/models/reviewRequestModel.js',
            'rb/js/resources/models/screenshotModel.js',
            'rb/js/resources/models/screenshotCommentModel.js',
            'rb/js/resources/models/screenshotCommentReplyModel.js',
            'rb/js/resources/collections/resourceCollection.js',
            'rb/js/models/userSessionModel.js',
        ),
        'output_filename': 'rb/js/base.min.js',
    },
    'reviews': {
        'source_filenames': (
            # Note: These are roughly in dependency order.
            'rb/js/models/abstractCommentBlockModel.js',
            'rb/js/models/abstractReviewableModel.js',
            'rb/js/models/commentEditorModel.js',
            'rb/js/models/commentIssueManagerModel.js',
            'rb/js/models/fileAttachmentCommentBlockModel.js',
            'rb/js/models/fileAttachmentReviewableModel.js',
            'rb/js/models/regionCommentBlockModel.js',
            'rb/js/models/reviewReplyEditorModel.js',
            'rb/js/models/reviewRequestEditorModel.js',
            'rb/js/models/imageReviewableModel.js',
            'rb/js/models/screenshotCommentBlockModel.js',
            'rb/js/models/screenshotReviewableModel.js',
            'rb/js/models/textBasedCommentBlockModel.js',
            'rb/js/models/textBasedReviewableModel.js',
            'rb/js/models/markdownReviewableModel.js',
            'rb/js/pages/models/diffViewerPageModel.js',
            'rb/js/pages/views/reviewablePageView.js',
            'rb/js/pages/views/reviewRequestPageView.js',
            'rb/js/pages/views/diffViewerPageView.js',
            'rb/js/utils/textUtils.js',
            'rb/js/views/abstractCommentBlockView.js',
            'rb/js/views/abstractReviewableView.js',
            'rb/js/views/collapsableBoxView.js',
            'rb/js/views/commentDialogView.js',
            'rb/js/views/commentIssueBarView.js',
            'rb/js/views/diffFragmentQueueView.js',
            'rb/js/views/dndUploaderView.js',
            'rb/js/views/draftReviewBannerView.js',
            'rb/js/views/fileAttachmentCommentBlockView.js',
            'rb/js/views/fileAttachmentReviewableView.js',
            'rb/js/views/fileAttachmentThumbnailView.js',
            'rb/js/views/floatingBannerView.js',
            'rb/js/views/issueSummaryTableView.js',
            'rb/js/views/regionCommentBlockView.js',
            'rb/js/views/reviewBoxListView.js',
            'rb/js/views/reviewBoxView.js',
            'rb/js/views/reviewDialogView.js',
            'rb/js/views/reviewReplyDraftBannerView.js',
            'rb/js/views/reviewReplyEditorView.js',
            'rb/js/views/reviewRequestEditorView.js',
            'rb/js/views/screenshotThumbnailView.js',
            'rb/js/views/imageReviewableView.js',
            'rb/js/views/textBasedCommentBlockView.js',
            'rb/js/views/textBasedReviewableView.js',
            'rb/js/views/markdownReviewableView.js',
            'rb/js/diffviewer/models/diffCommentBlockModel.js',
            'rb/js/diffviewer/models/diffCommentsHintModel.js',
            'rb/js/diffviewer/models/diffFileModel.js',
            'rb/js/diffviewer/models/diffReviewableModel.js',
            'rb/js/diffviewer/models/diffRevisionModel.js',
            'rb/js/diffviewer/models/paginationModel.js',
            'rb/js/diffviewer/collections/diffFileCollection.js',
            'rb/js/diffviewer/views/chunkHighlighterView.js',
            'rb/js/diffviewer/views/diffCommentBlockView.js',
            'rb/js/diffviewer/views/diffCommentsHintView.js',
            'rb/js/diffviewer/views/diffFileIndexView.js',
            'rb/js/diffviewer/views/diffReviewableView.js',
            'rb/js/diffviewer/views/diffRevisionLabelView.js',
            'rb/js/diffviewer/views/diffRevisionSelectorView.js',
            'rb/js/diffviewer/views/paginationView.js',
            'rb/js/diffviewer.js',
            'rb/js/reviews.js',
        ),
        'output_filename': 'rb/js/reviews.min.js',
    },
    'newReviewRequest': {
        'source_filenames': (
            # Note: These are roughly in dependency order.
            'rb/js/resources/models/repositoryBranchModel.js',
            'rb/js/resources/models/repositoryCommitModel.js',
            'rb/js/resources/collections/repositoryBranchesCollection.js',
            'rb/js/resources/collections/repositoryCommitsCollection.js',
            'rb/js/resources/models/repositoryModel.js',
            'rb/js/resources/models/validateDiffModel.js',
            'rb/js/newReviewRequest/models/postCommitModel.js',
            'rb/js/newReviewRequest/models/preCommitModel.js',
            'rb/js/newReviewRequest/models/newReviewRequestModel.js',
            'rb/js/views/collectionView.js',
            'rb/js/newReviewRequest/views/branchView.js',
            'rb/js/newReviewRequest/views/branchesView.js',
            'rb/js/newReviewRequest/views/commitView.js',
            'rb/js/newReviewRequest/views/commitsView.js',
            'rb/js/newReviewRequest/views/repositoryView.js',
            'rb/js/newReviewRequest/views/repositorySelectionView.js',
            'rb/js/newReviewRequest/views/postCommitView.js',
            'rb/js/newReviewRequest/views/preCommitView.js',
            'rb/js/newReviewRequest/views/newReviewRequestView.js',
        ),
        'output_filename': 'rb/js/newReviewRequest.min.js',
    },
    'admin': {
        'source_filenames': (
            'lib/js/jquery.masonry.js',
            'rb/js/admin.js',
        ),
        'output_filename': 'rb/js/admin.min.js',
    },
    'repositoryform': {
        'source_filenames': (
            'rb/js/repositoryform.js',
        ),
        'output_filename': 'rb/js/repositoryform.min.js',
    },
}, **DJBLETS_PIPELINE_JS)

PIPELINE_CSS = dict({
    'common': {
        'source_filenames': (
            'lib/css/jquery-ui-1.8.24.min.css',
            'rb/css/common.less',
            'rb/css/dashboard.less',
            'rb/css/icons.less',
            'rb/css/search.less',
        ),
        'output_filename': 'rb/css/common.min.css',
        'absolute_paths': False,
    },
    'js-tests': {
        'source_filenames': (
            'rb/css/js-tests.less',
        ),
        'output_filename': 'rb/css/js-tests.min.css',
        'absolute_paths': False,
    },
    'reviews': {
        'source_filenames': (
            'rb/css/diffviewer.less',
            'rb/css/dndUploader.less',
            'rb/css/image-review-ui.less',
            'rb/css/reviews.less',
            'rb/css/syntax.css',
        ),
        'output_filename': 'rb/css/reviews.min.css',
        'absolute_paths': False,
    },
    'newReviewRequest': {
        'source_filenames': (
            'rb/css/newReviewRequest.less',
        ),
        'output_filename': 'rb/css/newReviewRequest.min.css',
        'absolute_paths': False,
    },
    'admin': {
        'source_filenames': (
            'rb/css/admin.less',
            'rb/css/admin-dashboard.less',
        ),
        'output_filename': 'rb/css/admin.min.css',
        'absolute_paths': False,
    },
}, **DJBLETS_PIPELINE_CSS)

PIPELINE_CSS_COMPRESSOR = None
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.uglifyjs.UglifyJSCompressor'

# On production (site-installed) builds, we always want to use the pre-compiled
# versions. We want this regardless of the DEBUG setting (since they may
# turn DEBUG on in order to get better error output).
#
# On a build running out of a source tree, for testing purposes, we want to
# use the raw .less and JavaScript files when DEBUG is set. When DEBUG is
# turned off in a non-production build, though, we want to be able to play
# with the built output, so treat it like a production install.

if PRODUCTION or not DEBUG or os.getenv('FORCE_BUILD_MEDIA', ''):
    PIPELINE_COMPILERS = ['pipeline.compilers.less.LessCompiler']
    PIPELINE_ENABLED = True
elif DEBUG:
    PIPELINE_COMPILERS = []
    PIPELINE_ENABLED = False

# Packages to unit test
TEST_PACKAGES = ['reviewboard']

# URL Overrides
ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda u: reverse('user', kwargs={'username': u.username})
}
