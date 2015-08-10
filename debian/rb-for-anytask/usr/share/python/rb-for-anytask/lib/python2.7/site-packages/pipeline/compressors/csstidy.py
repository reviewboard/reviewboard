from __future__ import unicode_literals

from django.core.files import temp as tempfile

from pipeline.conf import settings
from pipeline.compressors import SubProcessCompressor


class CSSTidyCompressor(SubProcessCompressor):
    def compress_css(self, css):
        output_file = tempfile.NamedTemporaryFile(suffix='.pipeline')

        command = '%s - %s %s' % (
            settings.PIPELINE_CSSTIDY_BINARY,
            settings.PIPELINE_CSSTIDY_ARGUMENTS,
            output_file.name
        )
        self.execute_command(command, css)

        filtered_css = output_file.read()
        output_file.close()
        return filtered_css
