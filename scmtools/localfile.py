from scmtools.core import FileNotFoundError, SCMTool, HEAD

class LocalFileTool(SCMTool):
    def __init__(self, repository):
        self.repopath = repository.path

        if self.repopath[-1] == '/':
            self.repopath = self.repopath[:-1]

        SCMTool.__init__(self, repository)


    def get_file(self, path, revision=HEAD):
        if not path or revision != HEAD:
            raise FileNotFoundError(path, revision)

        try:
            fp = open(self.repopath + '/' + path, 'r')
            data = fp.read()
            fp.close()
            return data
        except IOError, e:
            raise FileNotFoundError(path, revision, str(e))

    def parse_diff_revision(self, file_str, revision_str):
        return file_str, HEAD

    def get_fields(self):
        return ['diff_path']
