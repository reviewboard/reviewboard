from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

class SCMException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class FileNotFoundException(Exception):
    def __init__(self, path, revision=None, detail=None):
        if revision == None or revision == HEAD:
            msg = "The file '%s' could not be found in the repository" % path
        else:
            msg = "The file '%s' (r%s) could not be found in the repository" \
                % (path, revision)
        Exception.__init__(self, msg)

        self.revision = revision
        self.path = path
        self.detail = detail


class Revision:
    pass

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

    def file_exists(self, path, revision=None):
        try:
            self.get_file(path, revision)
            return True
        except FileNotFoundException, e:
            return False

    def parse_diff_revision(self, revision_str):
        raise NotImplementedError

    def get_diffs_use_absolute_paths(self):
        return False

    def get_diff_header_info(self, header):
        raise NotImplementedError

    def get_changeset(self, changesetid):
        raise NotImplementedError

    def get_pending_changesets(self, userid):
        raise NotImplementedError

    def get_changeset(self, uri, userid):
        raise NotImplementedError


HEAD = Revision()

def get_tool():
    path = settings.SCMTOOL_BACKEND
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]

    try:
        mod = __import__(module, {}, {}, [attr])
    except ImportError, e:
        raise ImproperlyConfigured, \
            'Error importing SCM Tool %s: "%s"' % (module, e)

    try:
        cls = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured, \
            'Module "%s" does not define a "%s" SCM Tool' % (module, attr)

    return cls(settings.SCMTOOL_REPOPATH)
