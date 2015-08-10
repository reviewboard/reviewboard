#
# Settings for djblets.
#
# This is meant for internal use only. We use it primarily for building
# static media to bundle with djblets.
#
# This should generally not be used in a project.
from __future__ import unicode_literals

import os


SECRET_KEY = '47157c7ae957f904ab809d8c5b77e0209221d4c0'

USE_I18N = True

DEBUG = False
DJBLETS_ROOT = os.path.abspath(os.path.dirname(__file__))
HTDOCS_ROOT = os.path.join(DJBLETS_ROOT, 'htdocs')
STATIC_ROOT = os.path.join(HTDOCS_ROOT, 'static')
STATIC_URL = '/'

STATICFILES_DIRS = (
    os.path.join(DJBLETS_ROOT, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE_JS = {
    'djblets-config-forms': {
        'source_filenames': (
            'djblets/js/configForms/base.js',
            'djblets/js/configForms/collections/listItemsCollection.js',
            'djblets/js/configForms/models/listItemModel.js',
            'djblets/js/configForms/models/listModel.js',
            'djblets/js/configForms/views/listItemView.js',
            'djblets/js/configForms/views/listView.js',
            'djblets/js/configForms/views/pagesView.js',
            'djblets/js/configForms/views/tableItemView.js',
            'djblets/js/configForms/views/tableView.js',
        ),
        'output_filename': 'djblets/js/config-forms.min.js',
    },
    'djblets-datagrid': {
        'source_filenames': ('djblets/js/datagrid.js',),
        'output_filename': 'djblets/js/datagrid.min.js',
    },
    'djblets-extensions-admin': {
        'source_filenames': (
            'djblets/js/extensions/models/extensionManagerModel.js',
            'djblets/js/extensions/views/extensionManagerView.js',
        ),
        'output_filename': 'djblets/js/extensions-admin.min.js',
    },
    'djblets-extensions': {
        'source_filenames': (
            'djblets/js/extensions/base.js',
            'djblets/js/extensions/models/extensionModel.js',
            'djblets/js/extensions/models/extensionHookModel.js',
            'djblets/js/extensions/models/extensionHookPointModel.js',
        ),
        'output_filename': 'djblets/js/extensions.min.js',
    },
    'djblets-gravy': {
        'source_filenames': (
            # These are in dependency order
            'djblets/js/jquery.gravy.hacks.js',
            'djblets/js/jquery.gravy.util.js',
            'djblets/js/jquery.gravy.retina.js',
            'djblets/js/jquery.gravy.autosize.js',
            'djblets/js/jquery.gravy.inlineEditor.js',
            'djblets/js/jquery.gravy.modalBox.js',
            'djblets/js/jquery.gravy.tooltip.js',
            'djblets/js/jquery.gravy.funcQueue.js',
            'djblets/js/jquery.gravy.backboneUtils.js',
        ),
        'output_filename': 'djblets/js/jquery.gravy.min.js',
    },
    'djblets-js-tests': {
        'source_filenames': (
            'djblets/js/tests/backboneUtilsTests.js',
            'djblets/js/configForms/models/tests/listItemModelTests.js',
            'djblets/js/configForms/views/tests/listItemViewTests.js',
            'djblets/js/configForms/views/tests/listViewTests.js',
            'djblets/js/configForms/views/tests/tableItemViewTests.js',
            'djblets/js/configForms/views/tests/tableViewTests.js',
        ),
        'output_filename': 'djblets/js/tests.min.js',
    },
}

PIPELINE_CSS = {
    'djblets-admin': {
        'source_filenames': (
            'djblets/css/admin.less',
            'djblets/css/extensions.less',
        ),
        'output_filename': 'djblets/css/admin.min.css',
    },
    'djblets-config-forms': {
        'source_filenames': (
            'djblets/css/config-forms.less',
        ),
        'output_filename': 'djblets/css/config-forms.min.css',
    },
    'djblets-datagrid': {
        'source_filenames': (
            'djblets/css/datagrid.less',
        ),
        'output_filename': 'djblets/css/datagrid.min.css',
    },
}

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'djblets.auth',
    'djblets.datagrid',
    'djblets.extensions',
    'djblets.feedview',
    'djblets.gravatars',
    'djblets.log',
    'djblets.pipeline',
    'djblets.siteconfig',
    'djblets.testing',
    'djblets.util',
    'djblets.webapi',
]

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

if not DEBUG or os.getenv('FORCE_BUILD_MEDIA', ''):
    PIPELINE_COMPILERS = ['pipeline.compilers.less.LessCompiler']
    PIPELINE_ENABLED = True
elif DEBUG:
    PIPELINE_COMPILERS = []
    PIPELINE_ENABLED = False
