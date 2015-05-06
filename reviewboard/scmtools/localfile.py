from __future__ import unicode_literals

from django.utils import six

from reviewboard.scmtools.core import FileNotFoundError, SCMTool, HEAD


class LocalFileTool(SCMTool):
    name = "Local File"

    def __init__(self, repository):
        self.repopath = repository.path

        if self.repopath[-1] == '/':
            self.repopath = self.repopath[:-1]

        SCMTool.__init__(self, repository)

    def get_file(self, path, revision=HEAD, **kwargs):
        if not path or revision != HEAD:
            raise FileNotFoundError(path, revision)

        try:
            with open(self.repopath + '/' + path, 'rb') as f:
                return f.read()
        except IOError as e:
            raise FileNotFoundError(path, revision, detail=six.text_type(e))

    def parse_diff_revision(self, file_str, revision_str, *args, **kwargs):
        return file_str, HEAD

    def get_fields(self):
        return ['diff_path']
