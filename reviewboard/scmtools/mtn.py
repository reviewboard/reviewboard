from __future__ import unicode_literals

import os
import subprocess

from django.utils import six
from djblets.util.filesystem import is_exe_in_path

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.core import SCMTool
from reviewboard.scmtools.errors import FileNotFoundError, SCMError


class MonotoneTool(SCMTool):
    name = "Monotone"
    dependencies = {
        'executables': ['mtn'],
    }

    # Known limitations of this tool include:
    #    - It depends on a local database which we somehow need to determine
    #      how to update.
    #    - Binary files are not currently marked
    #    - Empty files cause the diff viewer to blow up.
    def __init__(self, repository):
        SCMTool.__init__(self, repository)
        self.client = MonotoneClient(repository.path)

    def get_file(self, path, revision=None, **kwargs):
        # revision is actually the file id here...
        if not revision:
            return b""

        return self.client.get_file(revision)

    def file_exists(self, path, revision=None, **kwargs):
        # revision is actually the file id here...
        if not revision:
            return False

        try:
            self.client.get_file(revision)
        except FileNotFoundError:
            return False

        return True

    def parse_diff_revision(self, file_str, revision_str, *args, **kwargs):
        return file_str, revision_str

    def get_diffs_use_absolute_paths(self):
        return True

    def get_fields(self):
        return ['diff_path', 'parent_diff_path']

    def get_parser(self, data):
        return MonotoneDiffParser(data)


class MonotoneDiffParser(DiffParser):
    INDEX_SEP = b"=" * 60

    def parse_special_header(self, linenum, info):
        if self.lines[linenum].startswith(b"#"):
            if b"is binary" in self.lines[linenum]:
                info['binary'] = True
                linenum += 1
            elif self.lines[linenum + 1] == self.INDEX_SEP:
                # This is a standard mtn diff header (comments with the file
                # summary)
                linenum += 1

        return linenum


class MonotoneClient:
    def __init__(self, path):
        if not is_exe_in_path('mtn'):
            # This is technically not the right kind of error, but it's the
            # pattern we use with all the other tools.
            raise ImportError

        self.path = path

        if not os.path.isfile(self.path):
            raise SCMError("Repository %s does not exist" % path)

    def get_file(self, fileid):
        args = ['mtn', '-d', self.path, 'automate', 'get_file', fileid]

        p = subprocess.Popen(args,
                             stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             close_fds=(os.name != 'nt'))

        out = p.stdout.read()
        err = six.text_type(p.stderr.read())
        failure = p.wait()

        if not failure:
            return out

        if "mtn: misuse: no file" in err:
            raise FileNotFoundError(fileid)
        else:
            raise SCMError(err)


# vi: et:sw=4 ts=4
