import urllib2
try:
    from urllib2 import quote as urllib_quote
except ImportError:
    from urllib import quote as urllib_quote

from reviewboard.diffviewer.parser import DiffParser, DiffParserError
from reviewboard.scmtools.core import \
    FileNotFoundError, SCMTool, HEAD, PRE_CREATION

class HgTool(SCMTool):
    def __init__(self, repository):
        SCMTool.__init__(self, repository)
        if repository.path.startswith('http'):
            self.client = HgWebClient(repository.path,
                                      repository.username,
                                      repository.password)
        else:
            self.client = HgClient(repository.path)

        self.uses_atomic_revisions = True
        self.diff_uses_changeset_ids = True

    def get_file(self, path, revision=HEAD):
        return self.client.cat_file(path, str(revision))

    def parse_diff_revision(self, file_str, revision_str):
        revision = revision_str
        if file_str == "/dev/null":
            revision = PRE_CREATION
        return file_str, revision

    def get_diffs_use_absolute_paths(self):
        return True

    def get_fields(self):
        return ['diff_path']

    def get_parser(self, data):
        return HgDiffParser(data)


class HgDiffParser(DiffParser):
    """
    This class is able to extract Mercurial changeset ids, and
    replaces /dev/null with a useful name
    """

    def parse_special_header(self, linenum, info):
        # XXX: does not handle git style diffs
        if self.lines[linenum].startswith("diff -r"):
            # diff between two revisions are in the following form:
            #  "diff -r abcdef123456 -r 123456abcdef filename"
            # diff between a revision and the working copy are like:
            #  "diff -r abcdef123456 filename"
            diffLine = self.lines[linenum].split()
            try:
                # hg is file based, so new file always == old file
                isCommitted = len(diffLine) > 4 and diffLine[3] == '-r'
                if isCommitted:
                    nameStartIndex = 5
                    info['newInfo'] = diffLine[4]
                else:
                    nameStartIndex = 3
                    info['newInfo'] = "Uncommitted"
                info['newFile'] = info['origFile'] = \
                    ' '.join(diffLine[nameStartIndex:])
                info['origInfo'] = diffLine[2]
                info['origChangesetId'] = diffLine[2]
            except ValueError:
                raise DiffParserError("The diff file is missing revision information",
                                      linenum)
            linenum += 1;

        return linenum

    def parse_diff_header(self, linenum, info):
        if linenum <= len(self.lines) and \
           self.lines[linenum].startswith("Binary file "):
            info['binary'] = True
            linenum += 1

        if linenum + 1 < len(self.lines) and \
           (self.lines[linenum].startswith('--- ') and \
             self.lines[linenum + 1].startswith('+++ ')):
            # check if we're a new file
            if self.lines[linenum].split()[1] == "/dev/null":
                info['origInfo'] = PRE_CREATION
            linenum += 2;
        return linenum


class HgWebClient:
    def __init__(self, repoPath, username, password):
        self.url = repoPath
        self.username = username
        self.password = password

    def cat_file(self, path, rev="tip"):
        if rev == HEAD:
            rev = "tip"
        elif rev == PRE_CREATION:
            rev = ""

        found = False

        for rawpath in ["raw-file", "raw"]:
            try:
                passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
                passman.add_password(None, self.url, self.username,
                                     self.password)
                authhandler = urllib2.HTTPBasicAuthHandler(passman)
                opener = urllib2.build_opener(authhandler)
                f = opener.open('%s/%s/%s/%s' %
                                (self.url, rawpath, rev, urllib_quote(path)))
                return f.read()
            except Exception, e:
                pass

        if not found:
            raise FileNotFoundError(path, rev, str(e))

    def get_filenames(self, rev):
        raise NotImplemented


class HgClient:
    def __init__(self, repoPath):
        from mercurial import hg, ui
        from mercurial.__version__ import version

        version_parts = [int(x) for x in version.split(".")]

        if version_parts[0] == 1 and version_parts[1] <= 2:
            hg_ui = ui.ui(interactive=False)
        else:
            hg_ui = ui.ui()
            hg_ui.setconfig('ui', 'interactive', 'off')

        self.repo = hg.repository(hg_ui, path=repoPath)

    def cat_file(self, path, rev="tip"):
        if rev == HEAD:
            rev = "tip"
        elif rev == PRE_CREATION:
            rev = ""
        try:
            return self.repo.changectx(rev).filectx(path).data()
        except Exception, e:
            # LookupError moves from repo to revlog in hg v0.9.4, so we
            # catch the more general Exception to avoid the dependency.
            raise FileNotFoundError(path, rev, str(e))

    def get_filenames(self, rev):
        return self.repo.changectx(rev).TODO
