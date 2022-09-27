"""Repository support for Bazaar."""

import os
import urllib.parse

import dateutil.parser
from django.utils.encoding import force_str
from django.utils.timezone import utc
from djblets.util.filesystem import is_exe_in_path

from reviewboard.scmtools.core import SCMClient, SCMTool, HEAD, PRE_CREATION
from reviewboard.scmtools.errors import (FileNotFoundError,
                                         InvalidRevisionFormatError,
                                         RepositoryNotFoundError, SCMError)
from reviewboard.ssh import utils as sshutils


# Register these URI schemes so we can handle them properly.
sshutils.ssh_uri_schemes.append('bzr+ssh')
urllib.parse.uses_netloc.extend(['bzr', 'bzr+ssh'])


_bzr_exe = None
_env_vars = {
    'PLUGIN_PATH': {
        'bzr': 'BZR_PLUGIN_PATH',
        'brz': 'BRZ_PLUGIN_PATH',
    },
    'SSH': {
        'bzr': 'BZR_SSH',
        'brz': 'BRZ_SSH',
    },
}


def get_bzr_exe():
    """Return the name of the executable used to run Bazaar/Breezy.

    If :command:`brz` is in :envvar:`PATH`, then ``brz`` will be returned.
    Otherwise, ``bzr`` will be returned, even if not found on the system.

    Version Added:
        4.0.7

    Returns:
        unicode:
        The name of the executable to run.
    """
    global _bzr_exe

    if _bzr_exe is None:
        if is_exe_in_path('brz'):
            # Breezy is installed, so we'll prefer that.
            _bzr_exe = 'brz'
        else:
            # Fall back to Bazaar, whether it's installed or not.
            _bzr_exe = 'bzr'

    return _bzr_exe


class BZRTool(SCMTool):
    """Repository support for Canonical's Bazaar or Breezy.

    Bazaar is one of the first distributed version control systems, often
    used with the `Launchpad <https://launchpad.net>`_ service, and available
    at http://bazaar.canonical.com/en/.

    In recent years, it's been deprecated, without any support for Python 3.
    A fork now exists called Breezy, available at https://www.breezy-vcs.org/.
    This is largely backwards-compatible, but uses a different command line
    name, plugin environment variables, and import paths. It's officially
    supported in Review Board 4.0.7 and up.

    Version Added:
        4.0.7:
        Added official support for Breezy.
    """

    scmtool_id = 'bazaar'

    # Ideally we'd change the name to "Bazaar / Breezy", but since names
    # historically have been used as tool IDs (RBTools uses it, for example),
    # we'd need to deprecate this usage entirely across the board before we
    # can rename it.
    name = 'Bazaar'

    dependencies = {
        'executables': [get_bzr_exe()],
    }

    # Timestamp format in bzr diffs.
    # This isn't totally accurate: there should be a %z at the end.
    # Unfortunately, strptime() doesn't support %z.
    DIFF_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

    # "bzr diff" indicates that a file is new by setting the old
    # timestamp to the epoch time.
    PRE_CREATION_TIMESTAMP = '1970-01-01 00:00:00 +0000'

    REVISION_SPEC_KEYWORDS = (
        'ancestor:',
        'annotate:',
        'before:',
        'branch:',
        'date:',
        'last:',
        'mainline:',
        'revid:',
        'revno:',
        'submit:',
        'tag:',
    )

    def __init__(self, repository):
        """Initialize the Bazaar tool.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to communicate with.
        """
        super(BZRTool, self).__init__(repository)

        if repository.local_site:
            local_site_name = repository.local_site.name
        else:
            local_site_name = None

        self.client = BZRClient(path=repository.path,
                                local_site_name=local_site_name)

    def get_file(self, path, revision, **kwargs):
        """Return the contents from a file with the given path and revision.

        Args:
            path (unicode):
                The path of the file within the repository. This must not be
                a full Bazaar repository path.

            revision (unicode):
                The revision to fetch. If a Bazaar revision specifier keyword
                is provided, then it will be used to perform the lookup.
                Otherwise, this is assumed to be a date in the form of
                ``YYYY-MM-DD HH:MM:SS ZZZZ``, the format used in Bazaar diffs.

            **kwargs (dict, unused):
                Unused additional keyword arguments.

        Returns:
            bytes:
            The contents of the file from the repository.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file at the given revision was not found in the repository.

            reviewboard.scmtools.errors.InvalidRevisionFormatError:
                The ``revision`` argument was in a format that's not supported.
        """
        if revision == BZRTool.PRE_CREATION_TIMESTAMP:
            return b''

        revspec = self._revspec_from_revision(revision)

        if revspec is None:
            raise InvalidRevisionFormatError(path, revision)

        return self.client.get_file(path=path, revspec=revspec)

    def file_exists(self, path, revision, **kwargs):
        """Return whether a file exists with the given path and revision.

        Args:
            path (unicode):
                The path of the file within the repository. This must not be
                a full Bazaar repository path.

            revision (unicode):
                The revision to fetch. If a Bazaar revision specifier keyword
                is provided, then it will be used to perform the lookup.
                Otherwise, this is assumed to be a date in the form of
                ``YYYY-MM-DD HH:MM:SS ZZZZ``, the format used in Bazaar diffs.

            **kwargs (dict, unused):
                Unused additional keyword arguments.

        Returns:
            bool:
            ``True`` if the file exists. ``False`` if it does not.

        Raises:
            reviewboard.scmtools.errors.InvalidRevisionFormatError:
                The ``revision`` argument was in a format that's not supported.
        """
        if revision == BZRTool.PRE_CREATION_TIMESTAMP:
            return False

        revspec = self._revspec_from_revision(revision)

        if revspec is None:
            raise InvalidRevisionFormatError(path, revision)

        return self.client.get_file_exists(path=path, revspec=revspec)

    def parse_diff_revision(self, filename, revision, *args, **kwargs):
        """Parse and return a filename and revision from a diff.

        If the revision identifier is a date indicating a new file, then
        this will return :py:data:`~reviewboard.scmtools.core.PRE_CREATION`.
        Otherwise, the revision identifier is returned directly.

        Args:
            filename (bytes):
                The filename in the diff.

            revision (bytes):
                The revision in the diff.

            **kwargs (dict, unused):
                Unused additional keyword arguments.

        Returns:
            tuple:
            A tuple containing two items:

            1. The normalized filename as a byte string.
            2. The normalized revision as a byte string or a
               :py:class:`~reviewboard.scmtools.core.Revision`.
        """
        if revision == BZRTool.PRE_CREATION_TIMESTAMP.encode('utf-8'):
            revision = PRE_CREATION

        return filename, revision

    def _revspec_from_revision(self, revision):
        """Return a Bazaar revision specification based on the given revision.

        If the revision starts with a Bazaar revision specifier keyword
        argument, then the revision will be used as-is (allowing for the `bzr
        diff-revid <https://launchpad.net/bzr-diff-revid>`_ plugin to be used).

        Otherwise, this will attempt to match a date in
        ``YYYY-MM-DD HH:MM:SS ZZZZ` format (used by Bazaar diffs).

        Args:
            revision (unicode):
                The revision to parse.

        Returns:
            unicode:
            A revision specifier for the given revision. If a supported
            revision was not provided, this will return ``None``.
        """
        if revision == HEAD:
            revspec = 'last:1'
        elif revision.startswith(self.REVISION_SPEC_KEYWORDS):
            revspec = revision
        else:
            # Attempt to parse this as a timestamp into a Bazaar date revision
            # specifier.
            try:
                timestamp = dateutil.parser.parse(revision).astimezone(utc)
                revspec = 'date:%s' % timestamp.strftime('%Y-%m-%d,%H:%M:%S')
            except ValueError:
                revspec = None

        return revspec

    @classmethod
    def check_repository(cls, path, username=None, password=None,
                         local_site_name=None, **kwargs):
        """Check a repository to test its validity.

        This checks if a Bazaar repository exists and can be connected to. If
        the repository could not be found, an exception will be raised.

        Args:
            path (unicode):
                The repository path.

            username (unicode):
                The optional username used to connect to the repository.

            password (unicode):
                The optional password used to connect to the repository.

            local_site_name (unicode):
                The name of the Local Site that will own the repository.

            **kwargs (dict, unused):
                Additional settings for the repository.

        Raises:
            reviewboard.scmtools.errors.RepositoryNotFoundError:
                The repository could not be found, or there was an error
                communicating with it.
        """
        super(BZRTool, cls).check_repository(path, username, password,
                                             local_site_name)

        client = BZRClient(path=path,
                           local_site_name=local_site_name)

        if not client.is_valid_repository():
            raise RepositoryNotFoundError()


class BZRClient(SCMClient):
    """A client for performing Bazaar requests.

    This invokes the command line :command:`bzr` tool to perform file and
    repository lookups.
    """

    _plugin_path = None

    def __init__(self, path, local_site_name):
        """Initialize the client.

        Args:
            path (unicode):
                The repository path provided by the user.

            local_site_name (unicode):
                The name of the Local Site owning the repository.
        """
        if path.startswith('/'):
            self.path = 'file://%s' % path
        else:
            self.path = path

        self.local_site_name = local_site_name

    def is_valid_repository(self):
        """Return whether the provided repository information is valid.

        Returns:
            bool:
            ``True`` if information on the repository could be found.
            ``False`` if not.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                There was an error talking to Bazaar.
        """
        p = self._run_bzr(['info', self.path])
        errmsg = force_str(p.stderr.read())
        ret_code = p.wait()

        self._check_error(errmsg)

        return ret_code == 0

    def get_file(self, path, revspec):
        """Return the contents of a file.

        This expects a path within the repository and a Bazaar revision
        specifier.

        Args:
            path (unicode):
                The path to the file within the repository.

            revspec (unicode):
                The Bazaar revision specifier used to look up the file.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be found.
        """
        path = self._build_repo_path(path)

        p = self._run_bzr(['cat', '-r', revspec, path])
        contents = p.stdout.read()
        errmsg = force_str(p.stderr.read())
        failure = p.wait()

        self._check_error(errmsg)

        if failure:
            raise FileNotFoundError(path=path,
                                    revision=revspec,
                                    detail=errmsg)

        return contents

    def get_file_exists(self, path, revspec):
        """Return whether a file exists in the repository.

        This expects a path within the repository and a Bazaar revision
        specifier.

        Args:
            path (unicode):
                The path to the file within the repository.

            revspec (unicode):
                The Bazaar revision specifier used to look up the file.

        Returns:
            bool:
            ``True`` if the file exists in the repository. ``False`` if not.
        """
        path = self._build_repo_path(path)
        p = self._run_bzr(['cat', '-r', revspec, path])
        errmsg = force_str(p.stderr.read())
        ret_code = p.wait()

        self._check_error(errmsg)

        return ret_code == 0

    def _run_bzr(self, args):
        """Run a Bazaar command.

        This will run :command:`bzr` with the specified arguments, and sets
        up the environment to work with :command:`rbssh`.

        Args:
            args (list of unicode):
                The list of arguments to pass to :command:`bzr`.

        Returns:
            subprocess.Popen:
            The handle for the process.
        """
        bzr_exe = get_bzr_exe()
        plugin_path_envvar = _env_vars['PLUGIN_PATH'][bzr_exe]
        ssh_envvar = _env_vars['SSH'][bzr_exe]

        if not BZRClient._plugin_path:
            BZRClient._plugin_path = (
                '%s:%s' % (
                    os.path.join(os.path.dirname(__file__), 'plugins',
                                 'bzrlib', 'plugins'),
                    os.environ.get(str(plugin_path_envvar), str('')),
                )
            ).rstrip(':')

        return SCMTool.popen(
            [bzr_exe] + args,
            local_site_name=self.local_site_name,
            env={
                plugin_path_envvar: BZRClient._plugin_path,
                ssh_envvar: 'rbssh',
                'TZ': 'UTC',
            })

    def _check_error(self, errmsg):
        """Check an error message from bzr and raise an exception if needed.

        If the error is an internal error, it will be raised, without the
        exception. If it's a known error that we can report better information
        on, then that information will be raised.

        Args:
            errmsg (unicode):
                The error message.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                A suitable error message, if an internal error was hit.
        """
        if 'Bazaar has encountered an internal error' in errmsg:
            if 'prefetch() takes exactly 2 arguments (1 given)' in errmsg:
                errmsg = ('Installed bzr and paramiko modules are '
                          'incompatible. See '
                          'https://bugs.launchpad.net/bzr/+bug/1524066')
            else:
                errmsg = errmsg.split(
                    'Traceback (most recent call last):')[0].strip()

            raise SCMError(errmsg)

    def _build_repo_path(self, path):
        """Return a path for a repository or file within a repository.

        The returned path is based on the repository path and the provided
        path within the repository. The resulting path can be passed to
        :py:meth:`_run_bzr`.

        Args:
            path (unicode):
                The path within the repository.

        Returns:
            unicode:
            The resulting repository path.
        """
        return '%s/%s' % (self.path, path.lstrip('/'))
