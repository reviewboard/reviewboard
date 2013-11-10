from djblets.util.compat.six.moves import range

from reviewboard.scmtools.core import Branch, Commit, HEAD, SCMTool
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.scmtools.git import GitTool


class TestTool(GitTool):
    name = 'Test'
    uses_atomic_revisions = True
    supports_authentication = True
    supports_post_commit = True

    def get_repository_info(self):
        return {
            'key1': 'value1',
            'key2': 'value2',
        }

    def get_fields(self):
        return ['basedir', 'diff_path']

    def get_diffs_use_absolute_paths(self):
        return False

    def get_branches(self):
        return [
            Branch('trunk', '5', True),
            Branch('branch1', '7', False),
        ]

    def get_commits(self, start):
        return [
            Commit('user%d' % i, str(i), '2013-01-01T%02d:00:00.0000000' % i,
                   'Commit %d' % i, str(i - 1))
            for i in range(int(start), 0, -1)
        ]

    @classmethod
    def check_repository(cls, path, *args, **kwargs):
        pass
