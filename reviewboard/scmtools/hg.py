import logging
import re

try:
    from urllib2 import quote as urllib_quote
except ImportError:
    from urllib import quote as urllib_quote

from pkg_resources import parse_version

from reviewboard.diffviewer.parser import DiffParser, DiffParserError
from reviewboard.scmtools.git import GitDiffParser
from reviewboard.scmtools.core import \
    FileNotFoundError, SCMClient, SCMTool, HEAD, PRE_CREATION, UNKNOWN
from reviewboard.scmtools.errors import RepositoryNotFoundError


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
            self.client = HgClient(repository.path, repository.local_site)

        self.uses_atomic_revisions = True

    def get_file(self, path, revision=HEAD):
        return self.client.cat_file(path, str(revision))

    def parse_diff_revision(self, file_str, revision_str, *args, **kwargs):
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

    @classmethod
    def check_repository(cls, path, username=None, password=None,
                         local_site_name=None):
        """Performs checks on a repository to test its validity."""
        super(HgTool, cls).check_repository(path, username, password,
                                            local_site_name)

        # Create a client. This will fail if the repository doesn't exist.
        if path.startswith('http'):
            HgWebClient(path, username, password)
        else:
            HgClient(path, local_site_name)


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
            self.origChangesetId:
            # diff is in the following form:
            #  "diff --git a/origfilename b/newfilename"
            # possibly followed by:
            #  "{copy|rename} from origfilename"
            #  "{copy|rename} from newfilename"
            self.isGitDiff = True
            info['origInfo'] = info['origChangesetId'] = self.origChangesetId
            if not self.newChangesetId:
                info['newInfo'] = "Uncommitted"
            else:
                info['newInfo'] = self.newChangesetId
            lineMatch = re.search(
                    r' a/(.*?) b/(.*?)( (copy|rename) from .*)?$',
                    self.lines[linenum])
            info['origFile'] = lineMatch.group(1)
            info['newFile'] = lineMatch.group(2)
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

    def get_orig_commit_id(self):
        return self.origChangesetId

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


class HgWebClient(SCMClient):
    FULL_FILE_URL = '%(url)s/%(rawpath)s/%(revision)s/%(quoted_path)s'

    def __init__(self, path, username, password):
        super(HgWebClient, self).__init__(path, username=username,
                                          password=password)

        logging.debug('Initialized HgWebClient with url=%r, username=%r',
                      self.path, self.username)

    def cat_file(self, path, rev="tip"):
        if rev == HEAD or rev == UNKNOWN:
            rev = "tip"
        elif rev == PRE_CREATION:
            rev = ""

        for rawpath in ["raw-file", "raw", "hg-history"]:
            try:
                base_url = self.path.rstrip('/')

                if rawpath == 'hg-history':
                    base_url = self.path[:self.path.rfind('/')]

                url = self.FULL_FILE_URL % {
                    'url': base_url,
                    'rawpath': rawpath,
                    'revision': rev,
                    'quoted_path': urllib_quote(path.lstrip('/')),
                }

                return self.get_file_http(url, path, rev)
            except Exception:
                # It failed. Error was logged and we may try again.
                pass

        raise FileNotFoundError(path, rev)


class HgClient(object):
    def __init__(self, repoPath, local_site):
        from mercurial import hg, ui, error

        # We've encountered problems getting the Mercurial version number.
        # Originally, we imported 'version' from mercurial.__version__,
        # which would sometimes return None.
        #
        # We are now trying to go through their version() function, if
        # available. That is likely the most reliable.
        try:
            from mercurial.util import version
            hg_version = version()
        except ImportError:
            # If version() wasn't available, we'll try to import __version__
            # ourselves, and then get 'version' from that.
            try:
                from mercurial import __version__
                hg_version = __version__.version
            except ImportError:
                # If that failed, we'll hard-code an empty string. This will
                # trigger the "<= 1.2" case below.
                hg_version = ''

        # If something gave us None, convert it to an empty string so
        # parse_version can accept it.
        if hg_version is None:
            hg_version = ''

        if parse_version(hg_version) <= parse_version("1.2"):
            hg_ui = ui.ui(interactive=False)
        else:
            hg_ui = ui.ui()
            hg_ui.setconfig('ui', 'interactive', 'off')

        # Check whether ssh is configured for mercurial. Assume that any
        # configured ssh is set up correctly for this repository.
        hg_ssh = hg_ui.config('ui', 'ssh')

        if not hg_ssh:
            logging.debug('Using rbssh for mercurial')
            hg_ui.setconfig('ui', 'ssh', 'rbssh --rb-local-site=%s'
                            % local_site)
        else:
            logging.debug('Found configured ssh for mercurial: %s' % hg_ssh)

        try:
            self.repo = hg.repository(hg_ui, path=repoPath)
        except error.RepoError, e:
            logging.error('Error connecting to Mercurial repository %s: %s'
                          % (repoPath, e))
            raise RepositoryNotFoundError

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
            raise FileNotFoundError(path, rev, detail=str(e))
