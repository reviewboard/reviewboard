from __future__ import unicode_literals

import os

try:
    from shlex import quote
except ImportError:
    from pipes import quote

from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.utils.encoding import smart_str, smart_bytes

from pipeline.conf import settings
from pipeline.exceptions import CompilerError
from pipeline.storage import default_storage
from pipeline.utils import to_class


class Compiler(object):
    def __init__(self, storage=default_storage, verbose=False):
        self.storage = storage
        self.verbose = verbose

    @property
    def compilers(self):
        return [to_class(compiler) for compiler in settings.PIPELINE_COMPILERS]

    def compile(self, paths, force=False):
        def _compile(input_path):
            for compiler in self.compilers:
                compiler = compiler(verbose=self.verbose, storage=self.storage)
                if compiler.match_file(input_path):
                    output_path = self.output_path(input_path, compiler.output_extension)
                    infile = finders.find(input_path)
                    outfile = self.output_path(infile, compiler.output_extension)
                    outdated = compiler.is_outdated(input_path, output_path)
                    try:
                        compiler.compile_file(quote(infile), quote(outfile),
                            outdated=outdated, force=force)
                    except CompilerError:
                        if not self.storage.exists(output_path) or settings.DEBUG:
                            raise
                    return output_path
            else:
                return input_path

        try:
            import multiprocessing
            from concurrent import futures
        except ImportError:
            return list(map(_compile, paths))
        else:
            with futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
                return list(executor.map(_compile, paths))

    def output_path(self, path, extension):
        path = os.path.splitext(path)
        return '.'.join((path[0], extension))


class CompilerBase(object):
    def __init__(self, verbose, storage):
        self.verbose = verbose
        self.storage = storage

    def match_file(self, filename):
        raise NotImplementedError

    def compile_file(self, infile, outfile, outdated=False, force=False):
        raise NotImplementedError

    def save_file(self, path, content):
        return self.storage.save(path, ContentFile(smart_str(content)))

    def read_file(self, path):
        file = self.storage.open(path, 'rb')
        content = file.read()
        file.close()
        return content

    def is_outdated(self, infile, outfile):
        try:
            return self.storage.modified_time(infile) > self.storage.modified_time(outfile)
        except (OSError, NotImplementedError):
            return True


class SubProcessCompiler(CompilerBase):
    def execute_command(self, command, content=None, cwd=None):
        import subprocess
        pipe = subprocess.Popen(command, shell=True, cwd=cwd,
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        if content:
            content = smart_bytes(content)
        stdout, stderr = pipe.communicate(content)
        if stderr.strip():
            raise CompilerError(stderr)
        if self.verbose:
            print(stderr)
        return stdout
