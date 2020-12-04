from __future__ import unicode_literals

import re

from django.utils import six
from django.utils.six.moves import range

from reviewboard.hostingsvcs.errors import HostingServiceError
from reviewboard.scmtools.core import Branch, Commit, ChangeSet
from reviewboard.scmtools.errors import SCMError
from reviewboard.scmtools.git import GitTool


class TestTool(GitTool):
    scmtool_id = 'test'
    name = 'Test'
    diffs_use_absolute_paths = False
    supports_post_commit = True
    supports_history = False

    _PATH_RE = re.compile(
        r'^(?:/(?P<type>data):)?(?P<path>[^;]+)'
        r'(?:;encoding=(?P<encoding>[a-z0-9_-]+))?$')

    def get_repository_info(self):
        return {
            'key1': 'value1',
            'key2': 'value2',
        }

    def get_branches(self):
        return [
            Branch(id='trunk', commit='5', default=True),
            Branch(id='branch1', commit='7', default=False),
        ]

    def get_commits(self, branch=None, start=None):
        if branch == 'bad:hosting-service-error':
            raise HostingServiceError('This is a HostingServiceError')
        elif branch == 'bad:scm-error':
            raise SCMError('This is a SCMError')

        return [
            Commit('user%d' % i, six.text_type(i),
                   '2013-01-01T%02d:00:00.0000000' % i,
                   'Commit %d' % i,
                   six.text_type(i - 1))
            for i in range(int(start or 10), 0, -1)
        ]

    def get_change(self, commit_id):
        if commit_id == 'bad:hosting-service-error':
            raise HostingServiceError('This is a HostingServiceError')
        elif commit_id == 'bad:scm-error':
            raise SCMError('This is a SCMError')

        return Commit(
            author_name='user1',
            id=commit_id,
            date='2013-01-01T00:00:00.0000000',
            message='Commit summary\n\nCommit description.',
            diff=b'\n'.join([
                b"diff --git a/FILE_FOUND b/FILE_FOUND",
                b"index 712544e4343bf04967eb5ea80257f6c64d6f42c7.."
                b"f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644",
                b"--- a/FILE_FOUND",
                b"+++ b/FILE_FOUND",
                b"@ -1,1 +1,1 @@",
                b"-blah blah",
                b"+blah",
                b"-",
                b"1.7.1",
            ]))

    def get_file(self, path, revision, **kwargs):
        """Return a file from the repository.

        This testing tool allows for special paths that allow callers to
        optionally define the data to return and the encoding to use for that
        data.

        If the path starts with ``/data:``, then what comes after will be
        returned as data (with a newline appended to the data). Otherwise,
        a standard ``Hello, world!\\n`` will be returned.

        If the path ends with ``;encoding=...``, then whatever is returned will
        be encoded in the specified encoding type.

        Args:
            path (unicode):
                The path to retrieve, optionally with custom data and an
                encoding.

            revision (unicode, unused):
                The revision to retrieve. This is ignored.

            **kwargs (dict, unused):
                Additional keyword arguments for the request.

        Returns:
            bytes:
            The resulting file contents.
        """
        m = self._PATH_RE.match(path)
        assert m

        path_type = m.group('type')
        path = m.group('path')
        encoding = m.group('encoding') or 'utf-8'

        if path_type == 'data':
            return b'%s\n' % path.encode(encoding)

        return 'Hello, world!\n'.encode(encoding)

    def file_exists(self, path, revision, **kwargs):
        if path == '/FILE_FOUND' or path.startswith('/data:'):
            return True

        return super(TestTool, self).file_exists(path, revision, **kwargs)

    @classmethod
    def check_repository(cls, path, *args, **kwargs):
        pass


class TestToolSupportsPendingChangeSets(TestTool):
    scmtool_id = 'test-supports-pending-changesets'
    supports_pending_changesets = True

    def get_changeset(self, changesetid, allow_empty=False):
        changeset = ChangeSet()
        changeset.changenum = changesetid
        changeset.description = 'Hello world!'
        changeset.pending = True
        if not allow_empty:
            changeset.files = ['README.md']
        changeset.summary = 'Added a README markdown to help explain what the'\
            ' repository is used for. Hopefully, this takes off.'
        changeset.testing_done = "None was performed"
        return changeset
