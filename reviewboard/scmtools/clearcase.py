"""ClearCase SCM provider."""

from __future__ import unicode_literals

import logging
import os
import platform
import re
import subprocess
import sys
import tempfile

from django.conf import settings
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.core import SCMTool, HEAD, PRE_CREATION
from reviewboard.scmtools.errors import SCMError, FileNotFoundError

# This specific import is necessary to handle the paths for
# cygwin enabled machines.
if sys.platform.startswith(('win', 'cygwin')):
    import ntpath as cpath
else:
    import posixpath as cpath


_cleartool = None


def get_cleartool():
    """Return the cleartool binary/path name.

    This allows the user to configure a custom path to cleartool, or use a
    wrapper, by setting CC_CTEXEC in the settings_local.py file.

    Returns:
        unicode:
        The name or path of cleartool to use.
    """
    global _cleartool

    if _cleartool is None:
        _cleartool = getattr(settings, 'CC_CTEXEC', None)

        if not _cleartool:
            _cleartool = 'cleartool'

        logging.debug('Using cleartool %s', _cleartool)

    return _cleartool


class ClearCaseTool(SCMTool):
    """ClearCase SCM provider."""

    scmtool_id = 'clearcase'
    name = 'ClearCase'
    field_help_text = {
        'path': _('The absolute path to the VOB.'),
    }
    dependencies = {
        'executables': [get_cleartool()],
    }

    # This regular expression can extract from extended_path pure system path.
    # It is construct from two main parts. The first match is everything from
    # beginning of line to the first occurrence of /. The second match is
    # parts between /main and numbers (file version). This patch assumes each
    # branch present in extended_path was derived from /main and there is no
    # file or directory called "main" in path.
    UNEXTENDED = re.compile(r'^(.+?)/|/?(.+?)/main/?.*?/([0-9]+|CHECKEDOUT)')

    # Currently, snapshot and dynamic views are supported. Automatic views and
    # webviews will be reported as VIEW_UNKNOWN.
    VIEW_SNAPSHOT, VIEW_DYNAMIC, VIEW_UNKNOWN = range(3)

    def __init__(self, repository):
        """Initialize the tool.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The associated repository object.
        """
        self.repopath = repository.path

        SCMTool.__init__(self, repository)

        self.viewtype = self._get_view_type(self.repopath)

        if self.viewtype == self.VIEW_SNAPSHOT:
            self.client = ClearCaseSnapshotViewClient(self.repopath)
        elif self.viewtype == self.VIEW_DYNAMIC:
            self.client = ClearCaseDynamicViewClient(self.repopath)
        else:
            raise SCMError('Unsupported view type.')

    @staticmethod
    def run_cleartool(cmdline, cwd=None, ignore_errors=False,
                      results_unicode=True):
        """Run cleartool with the given command line.

        Args:
            cmdline (list of unicode):
                The cleartool command-line to execute.

            cwd (unicode, optional):
                The working directory to use for the subprocess.

            ignore_errors (bool, optional):
                Whether to ignore error return codes.

            results_unicode (bool, optional):
                Whether to return unicode or bytes.

        Returns:
            bytes or unicode:
            The output from the command.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                The cleartool execution returned an error code.
        """
        popen_kwargs = {}

        if results_unicode:
            # Popen before Python 3.6 doesn't support the ``encoding``
            # parameter, so we have to use ``universal_newlines`` and then
            # decode later.
            if sys.version_info[:2] >= (3, 6):
                popen_kwargs['encoding'] = 'utf-8'
            else:
                popen_kwargs['universal_newlines'] = True

        # On Windows 7+, executing a process that is marked SUBSYSTEM_CONSOLE
        # (such as cleartool) will pop up a console window, even if output is
        # redirected to a pipe. This hot mess prevents that from happening. If
        # Popen gains a better API to do this, we should switch to that when
        # we can. See https://bugs.python.org/issue30082 for details.
        if sys.platform.startswith('win'):
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            popen_kwargs['startupinfo'] = si

        cmdline = [get_cleartool()] + cmdline

        logging.debug('Running %s', subprocess.list2cmdline(cmdline))

        p = subprocess.Popen(
            cmdline,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            **popen_kwargs)

        (results, error) = p.communicate()
        failure = p.returncode

        if failure and not ignore_errors:
            raise SCMError(error)

        # We did not specify ``encoding`` to Popen earlier, so decode now.
        if results_unicode and 'encoding' not in popen_kwargs:
            results = force_text(results)

        return results


    def unextend_path(self, extended_path):
        """Remove ClearCase revision and branch information from path.

        ClearCase paths contain additional information about branch and file
        version preceded by @@. This function removes these parts from the
        ClearCase path to make it more readable. For example this function
        converts the extended path::

            /vobs/comm@@/main/122/network@@/main/55/sntp
            @@/main/4/src@@/main/1/sntp.c@@/main/8

        to the the to regular path::

            /vobs/comm/network/sntp/src/sntp.c

        Args:
            extended_path (unicode):
                The path to convert.

        Returns:
            unicode:
            The bare filename.
        """
        if '@@' not in extended_path:
            return HEAD, extended_path

        # The result of regular expression search is a list of tuples. We must
        # flatten this to a single list. b is first because it frequently
        # occurs in tuples. Before that remove @@ from path.
        unextended_chunks = [
            b or a
            for a, b, foo in self.UNEXTENDED.findall(
                extended_path.replace('@@', ''))
        ]

        if sys.platform.startswith('win'):
            # Properly handle full (with drive letter) and UNC paths.
            if unextended_chunks[0].endswith(':'):
                unextended_chunks[0] = '%s\\' % unextended_chunks[0]
            elif unextended_chunks[0] == '/' or unextended_chunks[0] == os.sep:
                unextended_chunks[0] = '\\\\'

        # Purpose of realpath is remove parts like /./ generated by
        # ClearCase when vobs branch was fresh created.
        unextended_path = cpath.realpath(
            cpath.join(*unextended_chunks)
        )

        revision = extended_path.rsplit('@@', 1)[1]
        if revision.endswith('CHECKEDOUT'):
            revision = HEAD

        return (revision, unextended_path)

    def normalize_path_for_display(self, filename, extra_data=None, **kwargs):
        """Normalize a path from a diff for display to the user.

        This will strip away information about the branch, version, and
        repository path, returning an unextended path relative to the view.

        Args:
            filename (unicode):
                The filename/path to normalize.

            extra_data (dict, optional):
                Extra data stored for the diff this file corresponds to.
                This may be empty or ``None``. Subclasses should not assume the
                presence of anything here.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            unicode:
            The resulting filename/path.

        """
        return cpath.relpath(self.unextend_path(filename)[1], self.repopath)

    def get_repository_info(self):
        """Return repository information.

        Returns:
            dict:
            A dictionary containing information for the repository, including
            the VOB tag and UUID.
        """
        vobstag = self._get_vobs_tag(self.repopath)
        return {
            'repopath': self.repopath,
            'uuid': self._get_vobs_uuid(vobstag)
        }

    def _get_view_type(self, repopath):
        """Return the ClearCase view type for the given path.

        Args:
            repopath (unicode):
                The repository path.

        Returns:
            int:
            One of :py:attr:`VIEW_SNAPSHOT`, :py:attr:`VIEW_DYNAMIC`, or
            :py:attr:`VIEW_UNKNOWN`.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error occurred when finding the view type.
        """
        result = self.run_cleartool(
            ['lsview', '-full', '-properties', '-cview'],
            cwd=repopath)

        for line in result.splitlines(True):
            splitted = line.split(' ')

            if splitted[0] == 'Properties:':
                if 'snapshot' in splitted:
                    return self.VIEW_SNAPSHOT
                elif 'dynamic' in splitted:
                    return self.VIEW_DYNAMIC

        return self.VIEW_UNKNOWN

    def _get_vobs_tag(self, repopath):
        """Return the VOB tag for the given path.

        Args:
            repopath (unicode):
                The repository path.

        Returns:
            unicode:
            The VOB tag for the repository at the given path.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error occurred when finding the VOB tag.
        """
        result = self.run_cleartool(
            ['describe', '-short', 'vob:.'],
            cwd=repopath)

        return result.rstrip()

    def _get_vobs_uuid(self, vobstag):
        """Return the UUID for the given VOB tag.

        Args:
            vobstag (unicode):
                The VOB tag.

        Returns:
            unicode:
            The UUID associated with the given VOB tag.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error occurred when finding the UUID.
        """
        result = self.run_cleartool(
            ['lsvob', '-long', vobstag],
            cwd=self.repopath)

        for line in result.splitlines(True):
            if line.startswith('Vob family uuid:'):
                return line.split(' ')[-1].rstrip()

        raise SCMError('Unable to find family uuid for vob: %s' % vobstag)

    def _get_element_kind(self, extended_path):
        """Return the element type of a VOB element.

        Args:
            extended_path (unicode):
                The path of the element, including revision information.

        Returns:
            unicode:
            The element type of the given element.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error occurred when finding the element type.
        """
        result = self.run_cleartool(
            ['desc', '-fmt', '%m', extended_path],
            cwd=self.repopath)

        return result.strip()

    def get_file(self, extended_path, revision=HEAD, **kwargs):
        """Return content of file or list content of directory.

        Args:
            extended_path (unicode):
                The path of the element, including revision information.

            revision (reviewboard.scmtools.core.Revision, optional):
                Revision information. This will be either
                :py:data:`~reviewboard.scmtools.core.PRE_CREATION` (new file),
                or :py:data:`~reviewboard.scmtools.core.HEAD` (signifying to
                use the revision information included in ``extended_path``).

            **kwargs (dict, optional):
                Additional unused keyword arguments.

        Returns:
            bytes:
            The contents of the element.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The given ``extended_path`` did not match a valid element.

            reviewboard.scmtools.errors.SCMError:
                Another error occurred.
        """
        if not extended_path:
            raise FileNotFoundError(extended_path, revision)

        if revision == PRE_CREATION:
            return ''

        if self.viewtype == self.VIEW_SNAPSHOT:
            # Get the path to (presumably) file element (remove version)
            # The '@@' at the end of file_path is required.
            file_path = extended_path.rsplit('@@', 1)[0] + '@@'
            okind = self._get_element_kind(file_path)

            if okind == 'directory element':
                raise SCMError('Directory elements are unsupported.')
            elif okind == 'file element':
                output = self.client.cat_file(extended_path)
            else:
                raise FileNotFoundError(extended_path)
        else:
            if cpath.isdir(extended_path):
                output = self.client.list_dir(extended_path)
            elif cpath.exists(extended_path):
                output = self.client.cat_file(extended_path)
            else:
                raise FileNotFoundError(extended_path)

        return output

    def parse_diff_revision(self, filename, revision, *args, **kwargs):
        """Parse and return a filename and revision from a diff.

        In the diffs for ClearCase, the revision is actually part of the file
        path. The ``revision_str`` argument contains modification timestamps.

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
            'filename must be a byte string, not %r' % type(filename))
        assert isinstance(revision, bytes), (
            'revision must be a byte string, not %r' % type(revision))

        if filename.endswith(os.path.join(os.sep, 'main',
                                          '0').encode('utf-8')):
            revision = PRE_CREATION
        elif filename.endswith(b'CHECKEDOUT') or b'@@' not in filename:
            revision = HEAD
        else:
            revision = filename.rsplit(b'@@', 1)[1]

        return filename, revision

    def get_parser(self, data):
        """Return the diff parser for a ClearCase diff.

        Args:
            data (bytes):
                The diff data.

        Returns:
            ClearCaseDiffParser:
            The diff parser.
        """
        return ClearCaseDiffParser(data,
                                   self.repopath,
                                   self._get_vobs_tag(self.repopath))


class ClearCaseDiffParser(DiffParser):
    """Special parser for ClearCase diffs created with RBTools."""

    SPECIAL_REGEX = re.compile(r'^==== (\S+) (\S+) ====$')

    def __init__(self, data, repopath, vobstag):
        """Initialize the parser.

        Args:
            data (bytes):
                The diff data.

            repopath (unicode):
                The path to the repository.

            vobstag (unicode):
                The VOB tag for the repository.
        """
        self.repopath = repopath
        self.vobstag = vobstag
        super(ClearCaseDiffParser, self).__init__(data)

    def parse_diff_header(self, linenum, info):
        """Parse a diff header.

        Paths for the same file may differ from paths in developer view because
        it depends from configspec and this is custom so we translate oids,
        attached by RBTools, to filenames to get paths working well inside
        clearcase view on reviewboard side.

        Args:
            linenum (int):
                The line number to start parsing at.

            info (dict):
                The diff info data to populate.

        Returns:
            int:
            The line number after the end of the diff header.
        """
        # Because ==== oid oid ==== is present after each header
        # parse standard +++ and --- headers at the first place
        linenum = super(ClearCaseDiffParser, self).parse_diff_header(
            linenum, info)

        # Parse for filename.
        m = self.SPECIAL_REGEX.match(self.lines[linenum])

        if m:
            # When using ClearCase in multi-site mode, data replication takes
            # much time, including oid. As said above, oid is used to retrieve
            # filename path independent of developer view.
            # When an oid is not found on server side an exception is thrown
            # and review request submission fails.
            # However at this time origFile and newFile info have already been
            # filled by super.parse_diff_header and contain client side paths,
            # client side paths are enough to start reviewing.
            # So we can safely catch exception and restore client side paths
            # if not found.
            # Note: origFile and newFile attributes are not defined when
            # managing binaries, so init to '' as fallback.
            current_filename = info.get('origFile', '')

            try:
                info['origFile'] = self._oid2filename(m.group(1))
            except Exception:
                logging.debug('oid (%s) not found, get filename from client',
                              m.group(1))
                info['origFile'] = self.client_relpath(current_filename)

            current_filename = info.get('newFile', '')

            try:
                info['newFile'] = self._oid2filename(m.group(2))
            except Exception:
                logging.debug('oid (%s) not found, get filename from client',
                              m.group(2))
                info['newFile'] = self.client_relpath(current_filename)

            linenum += 1

            if (linenum < len(self.lines) and
                (self.lines[linenum].startswith((b'Binary files ',
                                                 b'Files ')))):
                # To consider filenames translated from oids
                # origInfo and newInfo keys must exists.
                # Other files already contain this values field
                # by timestamp from +++/--- diff header.
                info['origInfo'] = ''
                info['newInfo'] = ''

                # Binary files need add origInfo and newInfo manually
                # because they don't have diff's headers (only oids).
                info['binary'] = True
                linenum += 1

        return linenum

    def _oid2filename(self, oid):
        """Convert an oid to a filename.

        Args:
            oid (unicode):
                The given oid.

        Returns:
            unicode:
            The filename of the element relative to the repopath.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error occurred while finding the filename.
        """
        result = ClearCaseTool.run_cleartool(
            ['describe', '-fmt', '%En@@%Vn', 'oid:%s' % oid],
            cwd=self.repopath)

        drive = os.path.splitdrive(self.repopath)[0]

        if drive:
            result = os.path.join(drive, result)

        return cpath.relpath(result, self.repopath)

    def client_relpath(self, filename):
        """Normalize a client view path.

        Args:
            filename (unicode):
                A path in a client view.

        Returns:
            unicode:
            The relative path against the vobstag.
        """
        try:
            path, revision = filename.split('@@', 1)
        except ValueError:
            path = filename
            revision = None

        relpath = ''
        logging.debug('vobstag: %s, path: %s', self.vobstag, path)

        while True:
            # An error should be raised if vobstag cannot be reached.
            if path == '/':
                logging.debug('vobstag not found in path, use client filename')
                return filename

            # Vobstag reach, relpath can be returned.
            if path.endswith(self.vobstag):
                break

            path, basename = os.path.split(path)

            # Init relpath with basename.
            if len(relpath) == 0:
                relpath = basename
            else:
                relpath = os.path.join(basename, relpath)

        logging.debug('relpath: %s', relpath)

        if revision:
            relpath = relpath + '@@' + revision

        return relpath


class ClearCaseDynamicViewClient(object):
    """A client for ClearCase dynamic views."""

    def __init__(self, path):
        """Initialize the client.

        Args:
            path (unicode):
                The path of the view.
        """
        self.path = path

    def cat_file(self, extended_path):
        """Return the contents of a file at a given revision.

        Args:
            extended_path (unicode):
                The file to fetch. This includes revision information.

        Returns:
            bytes:
            The contents of the file.
        """
        # As we are in a dynamic view, we can use the extended pathname to
        # access the file directly.
        with open(extended_path, 'rb') as f:
            return f.read()

    def list_dir(self, extended_path):
        """Return a directory listing of the given path.

        Args:
            extended_path (unicode):
                The path to the directory. This includes revision information.

        Returns:
            unicode:
            The contents of the given directory.
        """
        # As we are in a dynamic view, we can use the extended pathname to
        # access the directory directly.
        return ''.join([
            '%s\n' % s
            for s in sorted(os.listdir(extended_path))
        ])


class ClearCaseSnapshotViewClient(object):
    """A client for ClearCase snapshot views."""

    def __init__(self, path):
        """Initialize the client.

        Args:
            path (unicode):
                The path of the view.
        """
        self.path = path

    def cat_file(self, extended_path):
        """Return the contents of a file at a given revision.

        Args:
            extended_path (unicode):
                The file to fetch. This includes revision information.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The given ``extended_path`` did not match a valid element.
        """
        # In a snapshot view, we cannot directly access the file. Use cleartool
        # to pull the desired revision into a temp file.
        temp = tempfile.NamedTemporaryFile()

        # Close and delete the existing file so we can write to it.
        temp.close()

        try:
            ClearCaseTool.run_cleartool(
                ['get', '-to', temp.name, extended_path])
        except SCMError:
            raise FileNotFoundError(extended_path)

        try:
            with open(temp.name, 'rb') as f:
                return f.read()
        except Exception:
            raise FileNotFoundError(extended_path)
        finally:
            try:
                os.unlink(temp.name)
            except Exception:
                pass
