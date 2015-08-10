from __future__ import unicode_literals

from pipeline.conf import settings
from pipeline.compressors import SubProcessCompressor


class CSSMinCompressor(SubProcessCompressor):
    def compress_css(self, css):
        command = "%s %s" % (settings.PIPELINE_CSSMIN_BINARY, settings.PIPELINE_CSSMIN_ARGUMENTS)
        return self.execute_command(command, css)
