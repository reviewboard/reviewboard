from __future__ import unicode_literals

from pipeline.conf import settings
from pipeline.compilers import SubProcessCompiler


class CoffeeScriptCompiler(SubProcessCompiler):
    output_extension = 'js'

    def match_file(self, path):
        return path.endswith('.coffee') or path.endswith('.litcoffee')

    def compile_file(self, infile, outfile, outdated=False, force=False):
        if not outdated and not force:
            return  # File doesn't need to be recompiled
        command = "%s -cp %s %s > %s" % (
            settings.PIPELINE_COFFEE_SCRIPT_BINARY,
            settings.PIPELINE_COFFEE_SCRIPT_ARGUMENTS,
            infile,
            outfile
        )
        return self.execute_command(command)
