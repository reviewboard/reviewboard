import json
import logging
from datetime import datetime
from urllib.parse import quote as urllib_quote, urlparse

from django.utils.encoding import force_str
from djblets.util.filesystem import is_exe_in_path

from reviewboard.diffviewer.parser import DiffParser, DiffParserError
from reviewboard.scmtools.core import (Branch, Commit, FileNotFoundError, HEAD,
                                       PRE_CREATION, SCMClient, SCMTool,
                                       UNKNOWN)
from reviewboard.scmtools.errors import SCMError
from reviewboard.scmtools.git import GitDiffParser, strip_git_symlink_mode


logger = logging.getLogger(__name__)


class HgTool(SCMTool):
    scmtool_id = 'mercurial'
    name = "Mercurial"
    diffs_use_absolute_paths = True
    supports_history = True
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
            base_commit_id = str(base_commit_id)

        return self.client.cat_file(
            path,
            str(revision),
            base_commit_id=base_commit_id)

    def parse_diff_revision(self, filename, revision, *args, **kwargs):
        """Parse and return a filename and revision from a diff.

        Args:
            filename (bytes):
                The filename as represented in the diff.

            revision (bytes):
                The revision as represented in the diff.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            tuple:
            A tuple containing two items:

            1. The normalized filename as a byte string.
            2. The normalized revision as a byte string or a
               :py:class:`~reviewboard.scmtools.core.Revision`.
        """
        assert isinstance(filename, bytes), (
            'filename must be a byte string, not %s' % type(filename))
        assert isinstance(revision, bytes), (
            'revision must be a byte string, not %s' % type(revision))

        if filename == b'/dev/null':
            revision = PRE_CREATION

        return filename, revision or UNKNOWN

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
        diff_parser_cls = self._get_diff_parser_cls(data)

        return diff_parser_cls(data)

    @classmethod
    def date_tuple_to_iso8601(cls, data):
        """Return isoformat date from JSON tuple date.

        Args:
            data (tuple of int):
                 A 2-tuple, where the first item is a unix timestamp
                 and the second is the timezone offset.

        Returns:
            unicode:
            Date of given data in ISO 8601 format.
        """
        return force_str(datetime.utcfromtimestamp(
            data[0] + (data[1] * -1)).isoformat())

    @classmethod
    def check_repository(cls, path, username=None, password=None,
                         local_site_name=None, **kwargs):
        """Check a repository configuration for validity.

        This should check if a repository exists and can be connected to.
        This will also check if the repository requires an HTTPS certificate.

        A failed result is returned as an exception. The exception may contain
        extra information, such as a human-readable description of the problem.
        If the repository is valid and can be connected to, no exception will
        be thrown.

        Args:
            path (unicode):
                The repository path.

            username (unicode, optional):
                The optional username for the repository.

            password (unicode, optional):
                The optional password for the repository.

            local_site_name (unicode, optional):
                The name of the :term:`Local Site` that owns this repository.
                This is optional.

            **kwargs (dict, unused):
                Additional settings for the repository.

        Raises:
            reviewboard.scmtools.errors.AuthenticationError:
                The provided username/password or the configured SSH key could
                not be used to authenticate with the repository.

            reviewboard.scmtools.errors.RepositoryNotFoundError:
                A repository could not be found at the given path.

            reviewboard.scmtools.errors.SCMError:
                There was a generic error with the repository or its
                configuration.  Details will be provided in the error message.

            reviewboard.ssh.errors.BadHostKeyError:
                An SSH path was provided, but the host key for the repository
                did not match the expected key.

            reviewboard.ssh.errors.SSHError:
                An SSH path was provided, but there was an error establishing
                the SSH connection.

            reviewboard.ssh.errors.SSHInvalidPortError:
                An SSH path was provided, but the port specified was not a
                valid number.

            Exception:
                An unexpected exception has ocurred. Callers should check
                for this and handle it.
        """
        result = urlparse(path)

        if result.scheme == 'ssh':
            raise SCMError('Mercurial over SSH is not supported.')

        super(HgTool, cls).check_repository(
            path=path,
            username=username,
            password=password,
            local_site_name=local_site_name,
            **kwargs)

        # Create a client. This will fail if the repository doesn't exist.
        if result.scheme in ('http', 'https'):
            HgWebClient(path, username, password)
        else:
            HgClient(path, local_site_name)

    def normalize_patch(self, patch, filename, revision):
        """Normalize the provided patch file.

        For Git-style diffs, this will update modes on new, changed, and
        deleted symlinks, stripping the symlink mode and making them appear
        as normal files. This will avoid any issues with applying the diff,
        and allow us to instead parse the symlink change as a regular file.

        Version Added:
            4.0.6

        Args:
            patch (bytes):
                The diff/patch file to normalize.

            filename (unicode):
                The name of the file being changed in the diff.

            revision (unicode):
                The revision of the file being changed in the diff.

        Returns:
            bytes:
            The resulting diff/patch file.
        """
        diff_parser_cls = self._get_diff_parser_cls(patch)

        if diff_parser_cls is HgGitDiffParser:
            patch = strip_git_symlink_mode(patch)

        return patch

    def _get_diff_parser_cls(self, data):
        """Return the diff parser class used for this file.

        Version Added:
            4.0.6

        Args:
            data (bytes):
                The diff content.

        Returns:
            type:
            The diff parser used to parse the file.
        """
        hg_position = data.find(b'diff -r')
        git_position = data.find(b'diff --git')

        if git_position > -1 and (git_position < hg_position or
                                  hg_position == -1):
            return HgGitDiffParser
        else:
            return HgDiffParser


class HgDiffParser(DiffParser):
    """Diff parser for native Mercurial diffs."""

    def __init__(self, data):
        """Initialize the parser.

        Args:
            data (bytes):
                The diff content to parse.

        Raises:
            TypeError:
                The provided ``data`` argument was not a ``bytes`` type.
        """
        super(HgDiffParser, self).__init__(data)

        self.orig_changeset_id = None

    def parse_special_header(self, linenum, parsed_file):
        """Parse a special diff header marking the start of a new file's info.

        This looks for some special markers found in Mercurial diffs, trying
        to find a ``Parent`` or a ``diff -r`` line.

        A ``Parent`` line specifies a changeset ID that will be used as the
        source revision for all files.

        A ``diff -r`` line contains information identifying the file's name
        and other details.

        Args:
            linenum (int):
                The line number to begin parsing.

            parsed_file (reviewboard.diffviewer.parser.ParsedDiffFile):
                The file currently being parsed.

        Returns:
            int:
            The next line number to parse.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing the special header. This may be
                a corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        diff_line = self.lines[linenum]
        split_line = diff_line.split()

        if diff_line.startswith(b'# Parent') and len(split_line) == 3:
            self.orig_changeset_id = split_line[2]
        elif diff_line.startswith(b'diff -r'):
            # A diff between two revisions are in the following form:
            #
            #     diff -r abcdef123456 -r 123456abcdef filename
            #
            # A diff between a revision and the working copy:
            #
            #     diff -r abcdef123456 filename
            try:
                # Ordinary hg diffs don't record renames, so a new file
                # is always equivalent to an old file.
                if len(split_line) > 4 and split_line[3] == b'-r':
                    # Committed revision
                    name_start_ix = 5
                    parsed_file.modified_file_details = split_line[4]
                else:
                    # Uncommitted revision
                    name_start_ix = 3
                    parsed_file.modified_file_details = b'Uncommitted'

                filename = b' '.join(split_line[name_start_ix:])

                parsed_file.orig_filename = filename
                parsed_file.orig_file_details = split_line[2]
                parsed_file.modified_filename = filename

                self.orig_changeset_id = split_line[2]
            except ValueError:
                raise DiffParserError('The diff file is missing revision '
                                      'information',
                                      linenum=linenum)

            linenum += 1

        return linenum

    def parse_diff_header(self, linenum, parsed_file):
        """Parse a standard header before changes made to a file.

        This will look for information indicating if the file is a binary file,
        and then attempt to parse the standard diff headers (``---`` and
        ``+++`` lines).

        Args:
            linenum (int):
                The line number to begin parsing.

            parsed_file (reviewboard.diffviewer.parser.ParsedDiffFile):
                The file currently being parsed.

        Returns:
            int:
            The next line number to parse.
        """
        lines = self.lines

        if (linenum <= len(lines) and
            lines[linenum].startswith(b'Binary file ')):
            parsed_file.binary = True
            linenum += 1

        if (linenum + 1 < len(lines) and
            (lines[linenum].startswith(b'--- ') and
             lines[linenum + 1].startswith(b'+++ '))):
            # Check if this is a new file.
            if lines[linenum].split()[1] == b'/dev/null':
                parsed_file.orig_file_details = PRE_CREATION

            # Check if this is a deleted file.
            if lines[linenum + 1].split()[1] == b'/dev/null':
                parsed_file.deleted = True

            linenum += 2

        return linenum

    def get_orig_commit_id(self):
        """Return the commit ID of the original revision for the diff.

        This returns the commit ID found in a previously-parsed ``# Parent``
        line. It will override the values being stored in
        :py:attr:`FileDiff.source_revision
        <reviewboard.diffviewer.models.filediff.FileDiff.source_revision>`.

        Returns:
            bytes:
            The commit ID to return.
        """
        return self.orig_changeset_id


class HgGitDiffParser(GitDiffParser):
    """Diff Parser for Git diffs generated by Mercurial.

    Mercurial-generated Git diffs contain additional metadata that need to
    be parsed in order to properly locate changes to files in a repository.
    """

    def parse(self):
        """Parse the diff.

        This will parse the diff, looking for changes to the file.

        It special-cases the default Git diff parsing to check for any
        ``# Node ID`` or ``# Parent`` lines found at the beginning of the
        file, which specify the new commit ID and the base commit ID,
        respectively.

        Returns:
            list of ParsedDiffFile:
            The resulting list of files.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing part of the diff. This may be a
                corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        lines = self.lines
        linenum = 0

        while lines[linenum].startswith(b'#'):
            line = lines[linenum]
            split_line = line.split()
            linenum += 1

            if line.startswith(b'# Node ID') and len(split_line) == 4:
                self.new_commit_id = split_line[3]
            elif line.startswith(b'# Parent') and len(split_line) == 3:
                self.base_commit_id = split_line[2]

        return super(HgGitDiffParser, self).parse()

    def get_orig_commit_id(self):
        """Return the commit ID of the original revision for the diff.

        This returns the commit ID found in a previously-parsed ``# Parent``
        line. It will override the values being stored in
        :py:attr:`FileDiff.source_revision
        <reviewboard.diffviewer.models.filediff.FileDiff.source_revision>`.

        Returns:
            bytes:
            The commit ID to return.
        """
        return self.base_commit_id


class HgWebClient(SCMClient):
    FULL_FILE_URL = '%(url)s/%(rawpath)s/%(revision)s/%(quoted_path)s'

    def __init__(self, path, username, password):
        super(HgWebClient, self).__init__(path, username=username,
                                          password=password)

        self.path_stripped = self.path.rstrip('/')
        logger.debug('Initialized HgWebClient with url=%r, username=%r',
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
            rsp = self._get_http_json('%s/json-branches' % self.path_stripped)
        except Exception as e:
            logger.exception('Cannot load branches from hgweb: %s', e)
            return results

        if rsp:
            results = [
                Branch(
                    id=data['branch'],
                    commit=data['node'],
                    default=(data['branch'] == 'default'))
                for data in rsp['branches']
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
            rsp = self._get_http_json('%s/json-rev/%s'
                                      % (self.path_stripped, revision))
        except Exception as e:
            logger.exception('Cannot load detail of changeset from hgweb: %s',
                             e)
            return None

        if not rsp:
            return None

        try:
            parent = rsp['parents'][0]
        except IndexError:
            parent = None

        return Commit(id=rsp['node'],
                      message=rsp['desc'],
                      author_name=rsp['user'],
                      date=HgTool.date_tuple_to_iso8601(rsp['date']),
                      parent=parent)

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
            rsp = self._get_http_json('%s/json-log/?rev=%s'
                                      % (self.path_stripped, query))
        except Exception as e:
            logger.exception('Cannot load commits from hgweb: %s', e)
            return []

        results = []

        if rsp:
            for data in rsp['entries']:
                try:
                    parent = data['parents'][0]
                except IndexError:
                    parent = None

                iso8601 = HgTool.date_tuple_to_iso8601(data['date'])
                changeset = Commit(id=data['node'],
                                   message=data['desc'],
                                   author_name=data['user'],
                                   date=iso8601,
                                   parent=parent)
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
            contents = self.get_file_http(
                url='%s/raw-rev/%s' % (self.path_stripped, revision),
                path='',
                revision='')
        except Exception as e:
            logger.exception('Cannot load patch from hgweb: %s', e)
            raise SCMError('Cannot load patch from hgweb')

        if contents:
            changeset = self._get_commit(revision)

            if changeset:
                changeset.diff = contents
                return changeset

        logger.error('Cannot load changeset %s from hgweb', revision)
        raise SCMError('Cannot load changeset %s from hgweb' % revision)

    def _get_http_json(self, url):
        """Return a JSON response from an HgWeb API endpoint.

        Args:
            url (unicode):
                The URL of the JSON payload to fetch.

        Returns:
            object:
            The deserialized JSON data.

        Raises:
            Exception:
                Fetching the file, decoding the payload, or deserializing
                the JSON has failed.
        """
        contents = self.get_file_http(url=url,
                                      path='',
                                      revision='',
                                      mime_type='application/json')

        if contents is None or contents == b'not yet implemented':
            return None

        return json.loads(contents.decode('utf-8'))


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
            for data in json.loads(force_str(p.stdout.read()))
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

        for data in json.loads(force_str(p.stdout.read())):
            try:
                parent = data['parents'][0]
            except IndexError:
                parent = None

            if parent is not None:
                parent = force_str(parent)

            results.append(Commit(
                id=data['node'],
                message=data['desc'],
                author_name=data['user'],
                date=HgTool.date_tuple_to_iso8601(data['date']),
                parent=parent))

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
            logger.debug('Using rbssh for mercurial')

            if self.local_site_name:
                hg_ssh = 'rbssh --rb-local-site=%s' % self.local_site_name
            else:
                hg_ssh = 'rbssh'

            self.default_args.extend([
                '--config', 'ui.ssh=%s' % hg_ssh,
            ])
        else:
            logger.debug('Found configured ssh for mercurial: %s' % hg_ssh)

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
