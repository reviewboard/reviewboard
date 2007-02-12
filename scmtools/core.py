from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class SCMException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class ChangeSet:
    def __init__(self):
        self.changenum = None
        self.summary = ""
        self.description = ""
        self.testing_done = ""
        self.branch = ""
        self.bugs_closed = []
        self.files = []


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


class Revision(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.name == str(other)

    def __repr__(self):
        return '<Revision: %s>' % self.name


HEAD = Revision("HEAD")
PRE_CREATION = Revision("PRE-CREATION")


class SCMTool:
    def __init__(self, repopath):
        self.repopath = repopath

    def get_file(self, path, revision=None):
        raise NotImplementedError

    def file_exists(self, path, revision=HEAD):
        try:
            self.get_file(path, revision)
            return True
        except FileNotFoundException, e:
            return False

    def parse_diff_revision(self, revision_str):
        raise NotImplementedError

    def get_diffs_use_absolute_paths(self):
        return False

    def get_changeset(self, changesetid):
        raise NotImplementedError

    def get_pending_changesets(self, userid):
        raise NotImplementedError


def get_tool(path = settings.SCMTOOL_BACKEND):
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
