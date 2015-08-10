from __future__ import unicode_literals

from pipeline.conf import settings
from pipeline.compressors import SubProcessCompressor


class YuglifyCompressor(SubProcessCompressor):
    def compress_common(self, content, compress_type, arguments):
        command = '%s --type=%s %s' % (settings.PIPELINE_YUGLIFY_BINARY, compress_type, arguments)
        return self.execute_command(command, content)

    def compress_js(self, js):
        return self.compress_common(js, 'js', settings.PIPELINE_YUGLIFY_JS_ARGUMENTS)

    def compress_css(self, css):
        return self.compress_common(css, 'css', settings.PIPELINE_YUGLIFY_CSS_ARGUMENTS)
