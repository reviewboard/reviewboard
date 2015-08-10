# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings as _settings

DEFAULTS = {
    'DEBUG': False,

    'PIPELINE_ENABLED': not _settings.DEBUG,

    'PIPELINE_ROOT': _settings.STATIC_ROOT,
    'PIPELINE_URL': _settings.STATIC_URL,

    'PIPELINE_STORAGE': 'pipeline.storage.PipelineFinderStorage',

    'PIPELINE_CSS_COMPRESSOR': 'pipeline.compressors.yuglify.YuglifyCompressor',
    'PIPELINE_JS_COMPRESSOR': 'pipeline.compressors.yuglify.YuglifyCompressor',
    'PIPELINE_COMPILERS': [],

    'PIPELINE_CSS': {},
    'PIPELINE_JS': {},

    'PIPELINE_TEMPLATE_NAMESPACE': "window.JST",
    'PIPELINE_TEMPLATE_EXT': ".jst",
    'PIPELINE_TEMPLATE_FUNC': "template",
    'PIPELINE_TEMPLATE_SEPARATOR': "_",

    'PIPELINE_DISABLE_WRAPPER': False,

    'PIPELINE_CSSTIDY_BINARY': '/usr/bin/env csstidy',
    'PIPELINE_CSSTIDY_ARGUMENTS': '--template=highest',

    'PIPELINE_YUGLIFY_BINARY': '/usr/bin/env yuglify',
    'PIPELINE_YUGLIFY_CSS_ARGUMENTS': '--terminal',
    'PIPELINE_YUGLIFY_JS_ARGUMENTS': '--terminal',

    'PIPELINE_YUI_BINARY': '/usr/bin/env yuicompressor',
    'PIPELINE_YUI_CSS_ARGUMENTS': '',
    'PIPELINE_YUI_JS_ARGUMENTS': '',

    'PIPELINE_CLOSURE_BINARY': '/usr/bin/env closure',
    'PIPELINE_CLOSURE_ARGUMENTS': '',

    'PIPELINE_UGLIFYJS_BINARY': '/usr/bin/env uglifyjs',
    'PIPELINE_UGLIFYJS_ARGUMENTS': '',

    'PIPELINE_CSSMIN_BINARY': '/usr/bin/env cssmin',
    'PIPELINE_CSSMIN_ARGUMENTS': '',

    'PIPELINE_COFFEE_SCRIPT_BINARY': '/usr/bin/env coffee',
    'PIPELINE_COFFEE_SCRIPT_ARGUMENTS': '',

    'PIPELINE_LIVE_SCRIPT_BINARY': '/usr/bin/env lsc',
    'PIPELINE_LIVE_SCRIPT_ARGUMENTS': '',

    'PIPELINE_SASS_BINARY': '/usr/bin/env sass',
    'PIPELINE_SASS_ARGUMENTS': '--update',

    'PIPELINE_STYLUS_BINARY': '/usr/bin/env stylus',
    'PIPELINE_STYLUS_ARGUMENTS': '',

    'PIPELINE_LESS_BINARY': '/usr/bin/env lessc',
    'PIPELINE_LESS_ARGUMENTS': '',

    'PIPELINE_MIMETYPES': (
        (b'text/coffeescript', '.coffee'),
        (b'text/less', '.less'),
        (b'text/javascript', '.js'),
        (b'text/x-sass', '.sass'),
        (b'text/x-scss', '.scss')
    ),

    'PIPELINE_EMBED_MAX_IMAGE_SIZE': 32700,
    'PIPELINE_EMBED_PATH': r'[/]?embed/',
}


class PipelineSettings(object):
    '''
    Lazy Django settings wrapper for Django Pipeline
    '''
    def __init__(self, wrapped_settings):
        self.wrapped_settings = wrapped_settings

    def __getattr__(self, name):
        if hasattr(self.wrapped_settings, name):
            return getattr(self.wrapped_settings, name)
        elif name in DEFAULTS:
            return DEFAULTS[name]
        else:
            raise AttributeError("'%s' setting not found" % name)

settings = PipelineSettings(_settings)
