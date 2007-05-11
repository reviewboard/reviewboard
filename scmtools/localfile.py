from scmtools.core import SCMException, FileNotFoundException, SCMTool
from scmtools.core import HEAD, PRE_CREATION

class LocalFileTool(SCMTool):
    def __init__(self, repository):
        self.repopath = repository.path

        if self.repopath[-1] == '/':
            self.repopath = self.repopath[:-1]

        SCMTool.__init__(self, repository)


    def get_file(self, path, revision=HEAD):
        if not path or revision != HEAD:
            raise FileNotFoundException(path, revision)

        try:
            fp = open(self.repopath + '/' + path, 'r')
            data = fp.read()
            fp.close()
            return data
        except IOError, e:
            raise FileNotFoundException(path, revision, str(e))

    def parse_diff_revision(self, revision_str):
        return HEAD
