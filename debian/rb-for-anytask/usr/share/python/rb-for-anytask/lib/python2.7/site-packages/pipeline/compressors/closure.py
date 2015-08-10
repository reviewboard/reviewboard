from __future__ import unicode_literals

from pipeline.conf import settings
from pipeline.compressors import SubProcessCompressor


class ClosureCompressor(SubProcessCompressor):
    def compress_js(self, js):
        command = '%s %s' % (settings.PIPELINE_CLOSURE_BINARY, settings.PIPELINE_CLOSURE_ARGUMENTS)
        return self.execute_command(command, js)
