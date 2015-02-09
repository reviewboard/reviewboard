from __future__ import unicode_literals

import logging
import os
import re

from django.utils import six
from django.utils.six.moves.urllib.parse import quote as urlquote
from django.utils.translation import ugettext_lazy as _
from djblets.util.filesystem import is_exe_in_path

from reviewboard.diffviewer.parser import DiffParser, DiffParserError, File
from reviewboard.scmtools.core import SCMClient, SCMTool, HEAD, PRE_CREATION
from reviewboard.scmtools.errors import (FileNotFoundError,
                                         InvalidRevisionFormatError,
                                         RepositoryNotFoundError,
                                         SCMError)
from reviewboard.ssh import utils as sshutils


GIT_DIFF_EMPTY_CHANGESET_SIZE = 3


try:
    import urlparse
    uses_netloc = urlparse.uses_netloc
    urllib_urlparse = urlparse.urlparse
except ImportError:
    import urllib.parse
    uses_netloc = urllib.parse.uses_netloc
    urllib_urlparse = urllib.parse.urlparse


# Register these URI schemes so we can handle them properly.
uses_netloc.append('git')


sshutils.register_rbssh('GIT_SSH')


class ShortSHA1Error(InvalidRevisionFormatError):
    def __init__(self, path, revision, *args, **kwargs):
        InvalidRevisionFormatError.__init__(
            self,
            path=path,
            revision=revision,
            detail=six.text_type(_('The SHA1 is too short. Make sure the diff '
                                   'is generated with `git diff '
                                   '--full-index`.')),
            *args, **kwargs)


class GitTool(SCMTool):
    """
    You can only use this tool with a locally available git repository.
    The repository path should be to the .git directory (important if
    you do not have a bare repositry).
    """
    name = "Git"
    supports_raw_file_urls = True
    field_help_text = {
        'path': _('For local Git repositories, this should be the path to a '
                  '.git directory that Review Board can read from. For remote '
                  'Git repositories, it should be the clone URL.'),
    }
    dependencies = {
        'executables': ['git']
    }

    def __init__(self, repository):
        super(GitTool, self).__init__(repository)

        local_site_name = None

        if repository.local_site:
            local_site_name = repository.local_site.name

        credentials = repository.get_credentials()

        self.client = GitClient(repository.path, repository.raw_file_url,
                                credentials['username'],
                                credentials['password'],
                                repository.encoding, local_site_name)

    def get_file(self, path, revision=HEAD):
        if revision == PRE_CREATION:
            return ""

        return self.client.get_file(path, revision)

    def file_exists(self, path, revision=HEAD):
        if revision == PRE_CREATION:
            return False

        try:
            return self.client.get_file_exists(path, revision)
        except (FileNotFoundError, InvalidRevisionFormatError):
            return False

    def parse_diff_revision(self, file_str, revision_str, moved=False,
                            copied=False, *args, **kwargs):
        revision = revision_str

        if file_str == "/dev/null":
            revision = PRE_CREATION
        elif (revision != PRE_CREATION and
              (not (moved or copied) or revision != '')):
            # Moved files with no changes has no revision,
            # so don't validate those.
            self.client.validate_sha1_format(file_str, revision)

        return file_str, revision

    def get_diffs_use_absolute_paths(self):
        return True

    def get_fields(self):
        return ['diff_path', 'parent_diff_path']

    def get_parser(self, data):
        return GitDiffParser(data)

    @classmethod
    def check_repository(cls, path, username=None, password=None,
                         local_site_name=None):
        """
        Performs checks on a repository to test its validity.

        This should check if a repository exists and can be connected to.
        This will also check if the repository requires an HTTPS certificate.

        The result is returned as an exception. The exception may contain
        extra information, such as a human-readable description of the problem.
        If the repository is valid and can be connected to, no exception
        will be thrown.
        """
        client = GitClient(path, local_site_name=local_site_name)

        super(GitTool, cls).check_repository(client.path, username, password,
                                             local_site_name)

        if not client.is_valid_repository():
            raise RepositoryNotFoundError()

        # TODO: Check for an HTTPS certificate. This will require pycurl.


class GitDiffParser(DiffParser):
    """
    This class is able to parse diffs created with Git
    """
    pre_creation_regexp = re.compile(b"^0+$")

    DIFF_GIT_LINE_RES = [
        # Match with a/ and b/ prefixes. Common case.
        re.compile(
            b'^diff --git'
            b' (?P<aq>")?a/(?P<orig_filename>[^"]+)(?(aq)")'
            b' (?P<bq>")?b/(?P<new_filename>[^"]+)(?(bq)")$'),

        # Match without a/ and b/ prefixes. Spaces are allowed only if using
        # quotes around the filename.
        re.compile(
            b'^diff --git'
            b' (?P<aq>")?(?!a/)(?P<orig_filename>(?(aq)[^"]|[^ ])+)(?(aq)")'
            b' (?P<bq>")?(?!b/)(?P<new_filename>(?(bq)[^"]|[^ ])+)(?(bq)")$'),

        # Match without a/ and b/ prefixes, without quotes, and with the
        # original and new names being identical.
        re.compile(
            b'^diff --git'
            b' (?!")(?!a/)(?P<orig_filename>[^"]+)(?!")'
            b' (?!")(?!b/)(?P<new_filename>(?P=orig_filename))(?!")$'),
    ]

    def parse(self):
        """
        Parses the diff, returning a list of File objects representing each
        file in the diff.
        """
        self.files = []
        i = 0
        preamble = b''

        while i < len(self.lines):
            next_i, file_info, new_diff = self._parse_diff(i)

            if file_info:
                self._ensure_file_has_required_fields(file_info)

                if preamble:
                    file_info.data = preamble + file_info.data
                    preamble = b''

                self.files.append(file_info)
            elif new_diff:
                # We found a diff, but it was empty and has no file entry.
                # Reset the preamble.
                preamble = b''
            else:
                preamble += self.lines[i] + b'\n'

            i = next_i

        if not self.files and preamble.strip() != b'':
            # This is probably not an actual git diff file.
            raise DiffParserError('This does not appear to be a git diff', 0)

        return self.files

    def _parse_diff(self, linenum):
        """Parses out one file from a Git diff

        This will return a tuple of the next line number, the file info
        (if any), and whether or not we've found a file (even if we decided
        not to record it).
        """
        if self.lines[linenum].startswith(b"diff --git"):
            parts = self._parse_git_diff(linenum)

            return parts[0], parts[1], True
        else:
            return linenum + 1, None, False

    def _parse_git_diff(self, linenum):
        # First check if it is a new file with no content or
        # a file mode change with no content or
        # a deleted file with no content
        # then skip

        # Now we have a diff we are going to use so get the filenames + commits
        diff_git_line = self.lines[linenum]

        file_info = File()
        file_info.data = diff_git_line + b'\n'
        file_info.binary = False

        linenum += 1

        # Check to make sure we haven't reached the end of the diff.
        if linenum >= len(self.lines):
            return linenum, None

        line = self.lines[linenum]

        # Parse the extended header to save the new file, deleted file,
        # mode change, file move, and index.
        if self._is_new_file(linenum):
            file_info.data += line + b"\n"
            linenum += 1
        elif self._is_deleted_file(linenum):
            file_info.data += line + b"\n"
            linenum += 1
            file_info.deleted = True
        elif self._is_mode_change(linenum):
            file_info.data += line + b"\n"
            file_info.data += self.lines[linenum + 1] + b"\n"
            linenum += 2

        if self._is_moved_file(linenum):
            rename_from = self.lines[linenum + 1]
            rename_to = self.lines[linenum + 2]

            file_info.origFile = rename_from[len(b'rename from '):]
            file_info.newFile = rename_to[len(b'rename to '):]

            file_info.data += line + b"\n"
            file_info.data += rename_from + b"\n"
            file_info.data += rename_to + b"\n"
            linenum += 3
            file_info.moved = True
        elif self._is_copied_file(linenum):
            copy_from = self.lines[linenum + 1]
            copy_to = self.lines[linenum + 2]

            file_info.origFile = copy_from[len(b'copy from '):]
            file_info.newFile = copy_to[len(b'copy to '):]

            file_info.data += line + b"\n"
            file_info.data += copy_from + b"\n"
            file_info.data += copy_to + b"\n"
            linenum += 3
            file_info.copied = True

        # Assume by default that the change is empty. If we find content
        # later, we'll clear this.
        empty_change = True

        if self._is_index_range_line(linenum):
            index_range = self.lines[linenum].split(None, 2)[1]

            if '..' in index_range:
                file_info.origInfo, file_info.newInfo = index_range.split("..")

            if self.pre_creation_regexp.match(file_info.origInfo):
                file_info.origInfo = PRE_CREATION

            file_info.data += self.lines[linenum] + b"\n"
            linenum += 1

        # Get the changes
        while linenum < len(self.lines):
            if self._is_git_diff(linenum):
                break
            elif self._is_binary_patch(linenum):
                file_info.binary = True
                file_info.data += self.lines[linenum] + b"\n"
                empty_change = False
                linenum += 1
                break
            elif self._is_diff_fromfile_line(linenum):
                orig_line = self.lines[linenum]
                new_line = self.lines[linenum + 1]

                orig_filename = orig_line[len(b'--- '):]
                new_filename = new_line[len(b'+++ '):]

                if orig_filename.startswith(b'a/'):
                    orig_filename = orig_filename[2:]

                if new_filename.startswith(b'b/'):
                    new_filename = new_filename[2:]

                if orig_filename == b'/dev/null':
                    file_info.origInfo = PRE_CREATION
                    file_info.origFile = new_filename
                else:
                    file_info.origFile = orig_filename

                if new_filename == b'/dev/null':
                    file_info.newFile = orig_filename
                else:
                    file_info.newFile = new_filename

                file_info.data += orig_line + b'\n'
                file_info.data += new_line + b'\n'
                linenum += 2
            else:
                empty_change = False
                linenum = self.parse_diff_line(linenum, file_info)

        if not file_info.origFile:
            # This file didn't have any --- or +++ lines. This usually means
            # the file was deleted or moved without changes. We'll need to
            # fall back to parsing the diff --git line, which is more
            # error-prone.
            assert not file_info.newFile

            self._parse_diff_git_line(diff_git_line, file_info, linenum)

        if isinstance(file_info.origFile, six.binary_type):
            file_info.origFile = file_info.origFile.decode('utf-8')

        if isinstance(file_info.newFile, six.binary_type):
            file_info.newFile = file_info.newFile.decode('utf-8')

        # For an empty change, we keep the file's info only if it is a new
        # 0-length file, a moved file, a copied file, or a deleted 0-length
        # file.
        if (empty_change and
            file_info.origInfo != PRE_CREATION and
            not (file_info.moved or file_info.copied or file_info.deleted)):
            # We didn't find any interesting content, so leave out this
            # file's info.
            #
            # Note that we may want to change this in the future to preserve
            # data like mode changes, but that will require filtering out
            # empty changes at the diff viewer level in a sane way.
            file_info = None

        return linenum, file_info

    def _parse_diff_git_line(self, diff_git_line, file_info, linenum):
        """Parses the "diff --git" line for filename information.

        Not all diffs have "---" and "+++" lines we can parse for the
        filenames. Git leaves these out if there aren't any changes made
        to the file.

        This function attempts to extract this information from the
        "diff --git" lines in the diff. It supports the following:

        * All filenames with quotes.
        * All filenames with a/ and b/ prefixes.
        * Filenames without quotes, prefixes, or spaces.
        * Filenames without quotes or prefixes, where the original and
          modified filenames are identical.
        """
        for regex in self.DIFF_GIT_LINE_RES:
            m = regex.match(diff_git_line)

            if m:
                file_info.origFile = m.group('orig_filename')
                file_info.newFile = m.group('new_filename')
                return

        raise DiffParserError(
            'Unable to parse the "diff --git" line for this file, due to '
            'the use of filenames with spaces or --no-prefix, --src-prefix, '
            'or --dst-prefix options.',
            linenum)

    def _is_new_file(self, linenum):
        return (linenum < len(self.lines) and
                self.lines[linenum].startswith(b'new file mode'))

    def _is_deleted_file(self, linenum):
        return (linenum < len(self.lines) and
                self.lines[linenum].startswith(b'deleted file mode'))

    def _is_mode_change(self, linenum):
        return (linenum + 1 < len(self.lines) and
                self.lines[linenum].startswith(b'old mode') and
                self.lines[linenum + 1].startswith(b'new mode'))

    def _is_copied_file(self, linenum):
        return (linenum + 2 < len(self.lines) and
                self.lines[linenum].startswith(b'similarity index') and
                self.lines[linenum + 1].startswith(b'copy from') and
                self.lines[linenum + 2].startswith(b'copy to'))

    def _is_moved_file(self, linenum):
        return (linenum + 2 < len(self.lines) and
                self.lines[linenum].startswith(b'similarity index') and
                self.lines[linenum + 1].startswith(b'rename from') and
                self.lines[linenum + 2].startswith(b'rename to'))

    def _is_index_range_line(self, linenum):
        return (linenum < len(self.lines) and
                self.lines[linenum].startswith(b'index '))

    def _is_git_diff(self, linenum):
        return self.lines[linenum].startswith(b'diff --git')

    def _is_binary_patch(self, linenum):
        line = self.lines[linenum]

        return (line.startswith(b"Binary file") or
                line.startswith(b"GIT binary patch"))

    def _is_diff_fromfile_line(self, linenum):
        return (linenum + 1 < len(self.lines) and
                (self.lines[linenum].startswith(b'--- ') and
                    self.lines[linenum + 1].startswith(b'+++ ')))

    def _ensure_file_has_required_fields(self, file_info):
        """Make sure that the file object has all expected fields.

        This is needed so that there aren't explosions higher up the chain when
        the web layer is expecting a string object.
        """
        for attr in ('origInfo', 'newInfo', 'data'):
            if getattr(file_info, attr) is None:
                setattr(file_info, attr, b'')


class GitClient(SCMClient):
    FULL_SHA1_LENGTH = 40

    schemeless_url_re = re.compile(
        r'^(?P<username>[A-Za-z0-9_\.-]+@)?(?P<hostname>[A-Za-z0-9_\.-]+):'
        r'(?P<path>.*)')

    def __init__(self, path, raw_file_url=None, username=None, password=None,
                 encoding='', local_site_name=None):
        super(GitClient, self).__init__(self._normalize_git_url(path),
                                        username=username,
                                        password=password)

        if not is_exe_in_path('git'):
            # This is technically not the right kind of error, but it's the
            # pattern we use with all the other tools.
            raise ImportError

        self.raw_file_url = raw_file_url
        self.encoding = encoding
        self.local_site_name = local_site_name
        self.git_dir = None

        url_parts = urllib_urlparse(self.path)

        if url_parts[0] == 'file':
            self.git_dir = url_parts[2]

            p = self._run_git(['--git-dir=%s' % self.git_dir, 'config',
                               'core.repositoryformatversion'])
            failure = p.wait()

            if failure:
                # See if we have a permissions error
                if not os.access(self.git_dir, os.R_OK):
                    raise SCMError(_("Permission denied accessing the local "
                                     "Git repository '%s'") % self.git_dir)
                else:
                    raise SCMError(_('Unable to retrieve information from '
                                     'local Git repository'))

    def is_valid_repository(self):
        """Checks if this is a valid Git repository."""
        p = self._run_git(['ls-remote', self.path, 'HEAD'])
        errmsg = p.stderr.read()
        failure = p.wait()

        if failure:
            logging.error("Git: Failed to find valid repository %s: %s" %
                          (self.path, errmsg))
            return False

        return True

    def get_file(self, path, revision):
        if self.raw_file_url:
            self.validate_sha1_format(path, revision)

            return self.get_file_http(self._build_raw_url(path, revision),
                                      path, revision)
        else:
            return self._cat_file(path, revision, "blob")

    def get_file_exists(self, path, revision):
        if self.raw_file_url:
            try:
                # We want to make sure we can access the file successfully,
                # without any HTTP errors. A successful access means the file
                # exists. The contents themselves are meaningless, so ignore
                # them. If we do successfully get the file without triggering
                # any sort of exception, then the file exists.
                self.get_file(path, revision)
                return True
            except Exception:
                return False
        else:
            contents = self._cat_file(path, revision, "-t")
            return contents and contents.strip() == "blob"

    def validate_sha1_format(self, path, sha1):
        """Validates that a SHA1 is of the right length for this repository."""
        if self.raw_file_url and len(sha1) != self.FULL_SHA1_LENGTH:
            raise ShortSHA1Error(path, sha1)

    def _run_git(self, args):
        """Runs a git command, returning a subprocess.Popen."""
        return SCMTool.popen(['git'] + args,
                             local_site_name=self.local_site_name)

    def _build_raw_url(self, path, revision):
        url = self.raw_file_url
        url = url.replace("<revision>", revision)
        url = url.replace("<filename>", urlquote(path))
        return url

    def _cat_file(self, path, revision, option):
        """
        Call git-cat-file(1) to get content or type information for a
        repository object.

        If called with just "commit", gets the content of a blob (or
        raises an exception if the commit is not a blob).

        Otherwise, "option" can be used to pass a switch to git-cat-file,
        e.g. to test or existence or get the type of "commit".
        """
        commit = self._resolve_head(revision, path)

        p = self._run_git(['--git-dir=%s' % self.git_dir, 'cat-file',
                           option, commit])
        contents = p.stdout.read()
        errmsg = six.text_type(p.stderr.read())
        failure = p.wait()

        if failure:
            if errmsg.startswith("fatal: Not a valid object name"):
                raise FileNotFoundError(commit)
            else:
                raise SCMError(errmsg)

        return contents

    def _resolve_head(self, revision, path):
        if revision == HEAD:
            if path == "":
                raise SCMError("path must be supplied if revision is %s"
                               % HEAD)
            return "HEAD:%s" % path
        else:
            return six.text_type(revision)

    def _normalize_git_url(self, path):
        if path.startswith('file://'):
            return path

        url_parts = urllib_urlparse(path)
        scheme = url_parts[0]
        netloc = url_parts[1]

        if scheme and netloc:
            return path

        m = self.schemeless_url_re.match(path)

        if m:
            path = m.group('path')

            if not path.startswith('/'):
                path = '/' + path

            return 'ssh://%s%s%s' % (m.group('username') or '',
                                     m.group('hostname'),
                                     path)

        return "file://" + path
