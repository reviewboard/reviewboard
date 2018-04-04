from __future__ import unicode_literals

import json
import logging
from datetime import datetime

from django.utils import six
from django.utils.six.moves.urllib.parse import quote as urllib_quote, urlparse
from djblets.util.filesystem import is_exe_in_path

from reviewboard.diffviewer.parser import DiffParser, DiffParserError
from reviewboard.scmtools.core import (Branch, Commit, FileNotFoundError, HEAD,
                                       PRE_CREATION, SCMClient, SCMTool,
                                       UNKNOWN)
from reviewboard.scmtools.errors import SCMError
from reviewboard.scmtools.git import GitDiffParser


class HgTool(SCMTool):
    name = "Mercurial"
    diffs_use_absolute_paths = True
    supports_post_commit = True
    dependencies = {
        'executables': ['hg'],
    }

    def __init__(self, repository):
        super(HgTool, self).__init__(repository)

        if repository.path.startswith('http'):
            credentials = repository.get_credentials()

            self.client = HgWebClient(repository.path,
                                      credentials['username'],
                                      credentials['password'])
        else:
            if not is_exe_in_path('hg'):
                # This is technically not the right kind of error, but it's the
                # pattern we use with all the other tools.
                raise ImportError

            self.client = HgClient(repository.path, repository.local_site)

    def get_file(self, path, revision=HEAD, base_commit_id=None, **kwargs):
        if base_commit_id is not None:
            base_commit_id = six.text_type(base_commit_id)

        return self.client.cat_file(
            path,
            six.text_type(revision),
            base_commit_id=base_commit_id)

    def parse_diff_revision(self, file_str, revision_str, *args, **kwargs):
        revision = revision_str
        if file_str == "/dev/null":
            revision = PRE_CREATION
        if not revision_str:
            revision = UNKNOWN
        return file_str, revision

    def get_branches(self):
        """Return open/inactive branches from repository.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The list of the branches.
        """
        return self.client.get_branches()

    def get_commits(self, branch=None, start=None):
        """Return changesets from repository.

        Args:
            branch (unicode, optional):
                An identifier name of branch.

            start (unicode, optional):
                An optional changeset revision to start with.

        Returns:
            reviewboard.scmtools.core.Commit:
            The commit object.
        """
        return self.client.get_commits(branch, start)

    def get_change(self, revision):
        """Return detailed information about a changeset.

        Receive changeset data and patch from repository.

        Args:
            revision (unicode):
                An identifier of changeset.

        Returns:
            reviewboard.scmtools.core.Commit:
            The commit object.
        """
        return self.client.get_change(revision)

    def get_parser(self, data):
        hg_position = data.find(b'diff -r')
        git_position = data.find(b'diff --git')

        if git_position > -1 and (git_position < hg_position or
                                  hg_position == -1):
            return HgGitDiffParser(data)
        else:
            return HgDiffParser(data)

    @classmethod
    def date_tuple_to_iso8601(self, data):
        """Return isoformat date from JSON tuple date.

        Args:
            data (tuple of int):
                 A 2-tuple, where the first item is a unix timestamp
                 and the second is the timezone offset.

        Returns:
            unicode:
            Date of given data in ISO 8601 format.
        """
        return datetime.utcfromtimestamp(data[0] + (data[1] * -1)).isoformat()

    @classmethod
    def check_repository(cls, path, username=None, password=None,
                         local_site_name=None):
        """Performs checks on a repository to test its validity."""
        result = urlparse(path)

        if result.scheme == 'ssh':
            raise SCMError('Mercurial over SSH is not supported.')

        super(HgTool, cls).check_repository(path, username, password,
                                            local_site_name)

        # Create a client. This will fail if the repository doesn't exist.
        if result.scheme in ('http', 'https'):
            HgWebClient(path, username, password)
        else:
            HgClient(path, local_site_name)


class HgDiffParser(DiffParser):
    """
    This class is able to extract Mercurial changeset ids, and
    replaces /dev/null with a useful name
    """

    def __init__(self, data):
        self.new_changeset_id = None
        self.orig_changeset_id = None

        return super(HgDiffParser, self).__init__(data)

    def parse_special_header(self, linenum, info):
        diff_line = self.lines[linenum]
        split_line = diff_line.split()

        if diff_line.startswith(b"# Node ID") and len(split_line) == 4:
            self.new_changeset_id = split_line[3]
        elif diff_line.startswith(b"# Parent") and len(split_line) == 3:
            self.orig_changeset_id = split_line[2]
        elif diff_line.startswith(b"diff -r"):
            # diff between two revisions are in the following form:
            #  "diff -r abcdef123456 -r 123456abcdef filename"
            # diff between a revision and the working copy are like:
            #  "diff -r abcdef123456 filename"
            try:
                # ordinary hg diffs don't record renames, so
                # new file always == old file
                if len(split_line) > 4 and split_line[3] == b'-r':
                    # Committed revision
                    name_start_ix = 5
                    info['newInfo'] = split_line[4]
                else:
                    # Uncommitted revision
                    name_start_ix = 3
                    info['newInfo'] = "Uncommitted"

                info['newFile'] = info['origFile'] = b' '.join(
                    split_line[name_start_ix:])
                info['origInfo'] = split_line[2]
                info['origChangesetId'] = split_line[2]
                self.orig_changeset_id = split_line[2]
            except ValueError:
                raise DiffParserError("The diff file is missing revision "
                                      "information", linenum)
            linenum += 1

        return linenum

    def parse_diff_header(self, linenum, info):
        if (linenum <= len(self.lines) and
            self.lines[linenum].startswith(b"Binary file ")):
            info['binary'] = True
            linenum += 1

        if self._check_file_diff_start(linenum, info):
            linenum += 2

        return linenum

    def get_orig_commit_id(self):
        return self.orig_changeset_id

    def _check_file_diff_start(self, linenum, info):
        if (linenum + 1 < len(self.lines) and
            (self.lines[linenum].startswith(b'--- ') and
             self.lines[linenum + 1].startswith(b'+++ '))):
            # check if we're a new file
            if self.lines[linenum].split()[1] == b"/dev/null":
                info['origInfo'] = PRE_CREATION

            # Check if this is a deleted file.
            if self.lines[linenum + 1].split()[1] == b'/dev/null':
                info['deleted'] = True

            return True
        else:
            return False


class HgGitDiffParser(GitDiffParser):
    """Parser for git diffs which understands mercurial headers."""

    def parse(self):
        """Parse the diff returning a list of File objects.

        This will first parse special mercurial headers if they exist
        and then use the GitDiffParser functionality to parse the
        remainder of the diff.
        """
        # We need to parse out the commit information from the
        # commented header mercurial outputs.
        linenum = 0

        while self.lines[linenum].startswith(b'#'):
            line = self.lines[linenum]
            split_line = line.split()
            linenum += 1

            if line.startswith(b"# Node ID") and len(split_line) == 4:
                self.new_commit_id = split_line[3]
            elif line.startswith(b"# Parent") and len(split_line) == 3:
                self.base_commit_id = split_line[2]

        return super(HgGitDiffParser, self).parse()

    def get_orig_commit_id(self):
        """Return base commit, either parsed from the header or None."""
        return self.base_commit_id


class HgWebClient(SCMClient):
    FULL_FILE_URL = '%(url)s/%(rawpath)s/%(revision)s/%(quoted_path)s'

    def __init__(self, path, username, password):
        super(HgWebClient, self).__init__(path, username=username,
                                          password=password)

        self.path_stripped = self.path.rstrip('/')
        logging.debug('Initialized HgWebClient with url=%r, username=%r',
                      self.path, self.username)

    def cat_file(self, path, rev='tip', base_commit_id=None):
        # If the base commit id is provided it should override anything
        # that was parsed from the diffs.
        if rev != PRE_CREATION and base_commit_id is not None:
            rev = base_commit_id

        if rev == HEAD or rev == UNKNOWN:
            rev = "tip"
        elif rev == PRE_CREATION:
            rev = ""

        for rawpath in ["raw-file", "raw", "hg-history"]:
            try:
                url = self.FULL_FILE_URL % {
                    'url': self.path_stripped,
                    'rawpath': rawpath,
                    'revision': rev,
                    'quoted_path': urllib_quote(path.lstrip('/')),
                }

                return self.get_file_http(url, path, rev)
            except Exception:
                # It failed. Error was logged and we may try again.
                pass

        raise FileNotFoundError(path, rev)

    def get_branches(self):
        """Return open/inactive branches from hgweb in JSON.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            A list of the branches.
        """
        results = []

        try:
            url = '%s/json-branches' % self.path_stripped
            contents = self.get_file_http(url, '', '', 'application/json')
        except Exception as e:
            logging.exception('Cannot load branches from hgweb: %s', e)
            return results

        if contents:
            results = [
                Branch(
                    id=data['branch'],
                    commit=data['node'],
                    default=(data['branch'] == 'default'))
                for data in json.loads(contents)['branches']
                if data['status'] != 'closed'
            ]

        return results

    def _get_commit(self, revision):
        """Return detailed information about a single changeset.

        Receive changeset from hgweb in JSON format.

        Args:
            revision (unicode):
                An identifier of changeset.

        Returns:
            reviewboard.scmtools.core.Commit:
            The commit object.
        """
        try:
            url = '%s/json-rev/%s' % (self.path_stripped, revision)
            contents = self.get_file_http(url, '', '', 'application/json')
        except Exception as e:
            logging.exception('Cannot load detail of changeset from hgweb: %s',
                              e)
            return None

        if contents:
            data = json.loads(contents)
            try:
                parent = data['parents'][0]
            except IndexError:
                parent = None

            return Commit(id=data['node'],
                          message=data['desc'],
                          author_name=data['user'],
                          date=HgTool.date_tuple_to_iso8601(data['date']),
                          parent=parent,
                          base_commit_id=parent)

        return None

    def get_commits(self, branch=None, start=None):
        """Return detailed information about a changeset.

        Receive changeset from hgweb in JSON format.

        Args:
            branch (unicode, optional):
                An optional branch name to filter by.

            start (unicode, optional):
                An optional changeset revision to start with.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The list of commit objects.
        """
        query_parts = []

        if start:
            query_parts.append('ancestors(%s)' % start)

        query_parts.append('branch(%s)' % (branch or '.'))

        query = '+and+'.join(query_parts)

        try:
            url = '%s/json-log/?rev=%s' % (self.path_stripped, query)
            contents = self.get_file_http(url, '', '', 'application/json')
        except Exception as e:
            logging.exception('Cannot load commits from hgweb: %s', e)
            return []

        results = []

        if contents and contents != '"not yet implemented"':
            for data in json.loads(contents)['entries']:
                try:
                    parent = data['parents'][0]
                except IndexError:
                    parent = None

                iso8601 = HgTool.date_tuple_to_iso8601(data['date'])
                changeset = Commit(id=data['node'],
                                   message=data['desc'],
                                   author_name=data['user'],
                                   date=iso8601,
                                   parent=parent,
                                   base_commit_id=parent)
                results.append(changeset)

        return results

    def get_change(self, revision):
        """Return detailed information about a changeset.

        This method retrieves the patch in JSON format from hgweb.

        Args:
            revision (unicode):
                An identifier of changeset

        Returns:
            reviewboard.scmtools.core.Commit:
            The commit object.
        """
        try:
            url = '%s/raw-rev/%s' % (self.path_stripped, revision)
            contents = self.get_file_http(url, '', '')
        except Exception as e:
            logging.exception('Cannot load patch from hgweb: %s', e)
            raise SCMError('Cannot load patch from hgweb')

        if contents:
            changeset = self._get_commit(revision)

            if changeset:
                changeset.diff = contents
                return changeset

        logging.error('Cannot load changeset %s from hgweb', revision)
        raise SCMError('Cannot load changeset %s from hgweb' % revision)


class HgClient(SCMClient):
    COMMITS_PAGE_LIMIT = '31'

    def __init__(self, path, local_site):
        super(HgClient, self).__init__(path)
        self.default_args = None

        if local_site:
            self.local_site_name = local_site.name
        else:
            self.local_site_name = None

    def cat_file(self, path, rev='tip', base_commit_id=None):
        # If the base commit id is provided it should override anything
        # that was parsed from the diffs.
        if rev != PRE_CREATION and base_commit_id is not None:
            rev = base_commit_id

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

    def get_branches(self):
        """Return open/inactive branches from repository in JSON.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The list of the branches.
        """
        p = self._run_hg(['branches', '--template', 'json'])

        if p.wait() != 0:
            raise SCMError('Cannot load branches: %s' % p.stderr.read())

        results = [
            Branch(
                id=data['branch'],
                commit=data['node'],
                default=(data['branch'] == 'default'))
            for data in json.load(p.stdout)
            if not data['closed']
        ]

        return results

    def _get_commits(self, revset):
        """Return a list of commit objects.

        This method calls the given revset and parses the returned
        JSON data to retrieve detailed information about changesets.

        Args:
            revset (list of unicode):
                Hg command line that will be executed with JSON
                template as log command.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The list of commit objects.
        """
        cmd = ['log'] + revset + ['--template', 'json']
        p = self._run_hg(cmd)

        if p.wait() != 0:
            raise SCMError('Cannot load commits: %s' % p.stderr.read())

        results = []

        for data in json.load(p.stdout):
            try:
                parent = data['parents'][0]
            except IndexError:
                parent = None

            results.append(Commit(
                id=data['node'],
                message=data['desc'],
                author_name=data['user'],
                date=HgTool.date_tuple_to_iso8601(data['date']),
                parent=parent,
                base_commit_id=parent))

        return results

    def get_commits(self, branch=None, start=None):
        """Return changesets from repository in JSON.

        Args:
            branch (unicode, optional):
                An identifier name of branch.

            start (unicode, optional):
                An optional changeset revision to start with.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The list of commit objects.
        """
        revisions = ''

        if start:
            revisions = '-r%s:0' % start

        revset = [revisions, '-l', self.COMMITS_PAGE_LIMIT]

        if branch:
            revset.extend(('-b', branch))

        return self._get_commits(revset)

    def get_change(self, revision):
        """Return detailed information about a changeset.

        Receive changeset data and patch from repository in JSON.

        Args:
            revision (unicode):
                An identifier of changeset.

        Returns:
            reviewboard.scmtools.core.Commit:
            The commit object.
        """
        revset = ['-r', revision]
        changesets = self._get_commits(revset)

        if changesets:
            commit = changesets[0]
            cmd = ['diff', '-c', revision]
            p = self._run_hg(cmd)

            if p.wait() != 0:
                e = p.stderr.read()
                raise SCMError('Cannot load patch %s: %s' % (revision, e))

            commit.diff = p.stdout.read()
            return commit

        raise SCMError('Cannot load changeset %s' % revision)

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
