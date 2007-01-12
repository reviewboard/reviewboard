class SCMException(Exception):
    pass

class Revision:
    pass

HEAD = Revision()

class DiffHeader:
    orig_file = None
    orig_revision = None
    new_file = None
    new_revision = None

class SCMTool:
    def __init__(self, repopath):
        self.repopath = repopath

    def get_file(self, path, revision=None):
        raise NotImplementedError

    def get_diff_header_info(self, header):
        raise NotImplementedError

    def get_changeset(self, changesetid):
        raise NotImplementedError

    def get_pending_changesets(self, userid):
        raise NotImplementedError

    def get_changeset(self, uri, userid):
        raise NotImplementedError
