from __future__ import unicode_literals

import logging
import re

from djblets.util.compat import six
from djblets.util.compat.six.moves.urllib.parse import quote as urllib_quote
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
        return self.client.cat_file(path, six.text_type(revision))

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
            linenum += 1

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
                if self._check_file_diff_start(linenum, info):
                    self.isGitDiff = False
                    linenum += 2
                    return linenum

                line = self.lines[linenum]
                if (line.startswith("Binary file") or
                    line.startswith("GIT binary")):
                    info['binary'] = True
                    linenum += 1
                elif (line.startswith("copy") or
                      line.startswith("rename") or
                      line.startswith("new") or
                      line.startswith("old") or
                      line.startswith("deleted") or
                      line.startswith("index")):
                    # Not interested, just pass over this one
                    linenum += 1
                else:
                    break

        return linenum

    def get_orig_commit_id(self):
        return self.origChangesetId

    def _check_file_diff_start(self, linenum, info):
        if (linenum + 1 < len(self.lines) and
            (self.lines[linenum].startswith('--- ') and
             self.lines[linenum + 1].startswith('+++ '))):
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


class HgClient(SCMClient):
    def __init__(self, path, local_site):
        super(HgClient, self).__init__(path)
        self.default_args = None

        if local_site:
            self.local_site_name = local_site.name
        else:
            self.local_site_name = None

    def cat_file(self, path, rev="tip"):
        if rev == HEAD:
            rev = "tip"
        elif rev == PRE_CREATION:
            rev = ""

        if path:
            p = self._run_hg(['cat', '--rev', rev, path])
            contents = p.stdout.read()
            failure = p.wait()

            if not failure:
                return contents

        raise FileNotFoundError(path, rev)

    def _calculate_default_args(self):
        self.default_args = [
            '--noninteractive',
            '--repository', self.path,
            '--cwd', self.path,
        ]

        # We need to query hg for the current SSH configuration. Note
        # that _run_hg is calling this function, and this function is then
        # (through _get_hg_config) calling _run_hg, but it's okay. Due to
        # having set a good default for self.default_args above, there's no
        # issue of an infinite loop.
        hg_ssh = self._get_hg_config('ui.ssh')

        if not hg_ssh:
            logging.debug('Using rbssh for mercurial')

            if self.local_site_name:
                hg_ssh = 'rbssh --rb-local-site=%s' % self.local_site_name
            else:
                hg_ssh = 'rbssh'

            self.default_args.extend([
                '--config', 'ui.ssh=%s' % hg_ssh,
            ])
        else:
            logging.debug('Found configured ssh for mercurial: %s' % hg_ssh)

    def _get_hg_config(self, config_name):
        p = self._run_hg(['showconfig', config_name])
        contents = p.stdout.read()
        failure = p.wait()

        if failure:
            # Just assume it's empty.
            return None

        return contents.strip()

    def _run_hg(self, args):
        """Runs the Mercurial command, returning a subprocess.Popen."""
        if not self.default_args:
            self._calculate_default_args()

        return SCMTool.popen(
            ['hg'] + self.default_args + args,
            local_site_name=self.local_site_name)
