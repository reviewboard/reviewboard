import pysvn

from reviewboard.scmtools.core import SCMException, FileNotFoundException, SCMTool
from reviewboard.scmtools.core import HEAD, PRE_CREATION

class SVNTool(SCMTool):
    def __init__(self, repository):
        self.repopath = repository.path
        if self.repopath[-1] == '/':
            self.repopath = self.repopath[:-1]

        SCMTool.__init__(self, repository)
        self.client = pysvn.Client()
        if repository.username:
            self.client.set_default_username(repository.username)
        if repository.password:
            self.client.set_default_password(repository.password)

        self.uses_atomic_revisions = True


    def get_file(self, path, revision=HEAD):
        if not path:
            raise FileNotFoundException(path, revision)

        try:
            return self.client.cat(self.__normalize_path(path),
                                   self.__normalize_revision(revision))
        except pysvn.ClientError, e:
            raise FileNotFoundException(path, revision, str(e))


    def parse_diff_revision(self, file_str, revision_str):
        if revision_str == "(working copy)":
            return file_str, HEAD
        elif revision_str.startswith("(revision "):
            revision = revision_str.split()[1][:-1]

            if revision == "0":
                revision = PRE_CREATION

            return file_str, revision
        else:
            raise SCMException("Unable to parse diff revision header '%s'" %
                               revision_str)


    def get_filenames_in_revision(self, revision):
        r = self.__normalize_revision(revision)
        logs = self.client.log(self.repopath, r, r, True)

        if len(logs) == 0:
            return []
        elif len(logs) == 1:
            return [f['path'] for f in logs[0]['changed_paths']]
        else:
            assert False

    def __normalize_revision(self, revision):
        if revision == HEAD:
            r = pysvn.Revision(pysvn.opt_revision_kind.head)
        elif revision == PRE_CREATION:
            raise FileNotFoundException(path, revision)
        else:
            r = pysvn.Revision(pysvn.opt_revision_kind.number, str(revision))

        return r

    def __normalize_path(self, path):
        if path.startswith(self.repopath):
            return path
        elif path[0] == '/':
            return self.repopath + path
        else:
            return self.repopath + "/" + path
