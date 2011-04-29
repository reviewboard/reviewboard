import logging
import urllib2

try:
    from urllib2 import quote as urllib_quote
except ImportError:
    from urllib import quote as urllib_quote

from reviewboard.diffviewer.parser import DiffParser, DiffParserError
from reviewboard.scmtools.git import GitDiffParser
from reviewboard.scmtools.core import \
    FileNotFoundError, SCMTool, HEAD, PRE_CREATION, UNKNOWN


class HgTool(SCMTool):
    name = "Mercurial"
    supports_authentication = True
    dependencies = {
        'modules': ['mercurial'],
    }

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
        if not revision_str:
            revision = UNKNOWN
        return file_str, revision

    def get_diffs_use_absolute_paths(self):
        return True

    def get_fields(self):
        return ['diff_path', 'parent_diff_path']

    def get_parser(self, data):
        if data.lstrip().startswith('diff --git'):
            return GitDiffParser(data)
        else:
            return HgDiffParser(data)


class HgDiffParser(DiffParser):
    """
    This class is able to extract Mercurial changeset ids, and
    replaces /dev/null with a useful name
    """
    newChangesetId = None
    origChangesetId = None
    isGitDiff = False

    def parse_special_header(self, linenum, info):
        diffLine = self.lines[linenum].split()

        # git style diffs are supported as long as the node ID and parent ID
        # are present in the patch header
        if self.lines[linenum].startswith("# Node ID") and len(diffLine) == 4:
            self.newChangesetId = diffLine[3]
        elif self.lines[linenum].startswith("# Parent") and len(diffLine) == 3:
            self.origChangesetId = diffLine[2]
        elif self.lines[linenum].startswith("diff -r"):
            # diff between two revisions are in the following form:
            #  "diff -r abcdef123456 -r 123456abcdef filename"
            # diff between a revision and the working copy are like:
            #  "diff -r abcdef123456 filename"
            self.isGitDiff = False
            try:
                # ordinary hg diffs don't record renames, so
                # new file always == old file
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
                raise DiffParserError("The diff file is missing revision "
                                      "information", linenum)
            linenum += 1;

        elif self.lines[linenum].startswith("diff --git") and \
            self.origChangesetId and diffLine[2].startswith("a/") and \
            diffLine[3].startswith("b/"):
            # diff is in the following form:
            #  "diff --git a/origfilename b/newfilename"
            # possibly followed by:
            #  "{copy|rename} from origfilename"
            #  "{copy|rename} from newfilename"
            self.isGitDiff = True
            info['origInfo'] = info['origChangesetId' ] = self.origChangesetId
            if not self.newChangesetId:
                info['newInfo'] = "Uncommitted"
            else:
                info['newInfo'] = self.newChangesetId
            info['origFile'] = diffLine[2][2:]
            info['newFile'] = diffLine[3][2:]
            linenum += 1

        return linenum

    def parse_diff_header(self, linenum, info):
        if not self.isGitDiff:
            if linenum <= len(self.lines) and \
               self.lines[linenum].startswith("Binary file "):
                info['binary'] = True
                linenum += 1

            if self._check_file_diff_start(linenum, info):
                linenum += 2

        else:
            while linenum < len(self.lines):
                if self._check_file_diff_start(linenum, info ):
                    self.isGitDiff = False
                    linenum += 2
                    return linenum

                line = self.lines[linenum]
                if line.startswith("Binary file") or \
                   line.startswith("GIT binary"):
                    info['binary'] = True
                    linenum += 1
                elif line.startswith("copy") or \
                   line.startswith("rename") or \
                   line.startswith("new") or \
                   line.startswith("old") or \
                   line.startswith("deleted") or \
                   line.startswith("index"):
                    # Not interested, just pass over this one
                    linenum += 1
                else:
                    break

        return linenum

    def _check_file_diff_start(self, linenum, info):
        if linenum + 1 < len(self.lines) and \
           (self.lines[linenum].startswith('--- ') and \
             self.lines[linenum + 1].startswith('+++ ')):
            # check if we're a new file
            if self.lines[linenum].split()[1] == "/dev/null":
                info['origInfo'] = PRE_CREATION
            return True
        else:
            return False

class HgWebClient(object):
    FULL_FILE_URL = '%(url)s/%(rawpath)s/%(revision)s/%(quoted_path)s'

    def __init__(self, repoPath, username, password):
        self.url = repoPath
        self.username = username
        self.password = password
        logging.debug('Initialized HgWebClient with url=%r, username=%r',
                      self.url, self.username)

    def cat_file(self, path, rev="tip"):
        if rev == HEAD or rev == UNKNOWN:
            rev = "tip"
        elif rev == PRE_CREATION:
            rev = ""

        found = False

        for rawpath in ["raw-file", "raw"]:
            full_url = ''

            try:
                passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
                passman.add_password(None, self.url, self.username,
                                     self.password)
                authhandler = urllib2.HTTPBasicAuthHandler(passman)
                opener = urllib2.build_opener(authhandler)
                full_url = self.FULL_FILE_URL % {
                    'url': self.url.rstrip('/'),
                    'rawpath': rawpath,
                    'revision': rev,
                    'quoted_path': urllib_quote(path.lstrip('/')),
                }
                f = opener.open(full_url)
                return f.read()

            except urllib2.HTTPError, e:

                if e.code != 404:
                    logging.error("%s: HTTP error code %d when fetching "
                                  "file from %s: %s", self.__class__.__name__,
                                  e.code, full_url, e)

            except Exception:
                logging.exception('%s: Non-HTTP error when fetching %r: ',
                                  self.__class__.__name__, full_url)

        if not found:
            raise FileNotFoundError(path, rev, str(e))

    def get_filenames(self, rev):
        raise NotImplemented


class HgClient(object):

    def __init__(self, repoPath):
        from mercurial import hg, ui
        from mercurial.__version__ import version

        version_parts = [int(x) for x in version.split(".")]

        if version_parts[0] == 1 and version_parts[1] <= 2:
            hg_ui = ui.ui(interactive=False)
        else:
            hg_ui = ui.ui()
            hg_ui.setconfig('ui', 'interactive', 'off')

        hg_ui.setconfig('ui', 'ssh', 'rbssh')

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
