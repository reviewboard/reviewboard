from reviewboard.scmtools.core import HEAD, SCMTool
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

    @classmethod
    def check_repository(cls, path, *args, **kwargs):
        pass
