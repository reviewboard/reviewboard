"""Base backend support for Subversion clients."""

from urllib.parse import quote

from django.utils.translation import gettext as _

from reviewboard.scmtools.core import HEAD
from reviewboard.scmtools.errors import SCMError


class Client(object):
    """Base class for a Subversion client."""

    #: The default start revision for log entries.
    LOG_DEFAULT_START = 'HEAD'

    #: The default end revision for log entries.
    LOG_DEFAULT_END = '1'

    def __init__(self, config_dir, repopath, username=None, password=None):
        """Initialize the client.

        Args:
            config_dir (str):
                The path to the Subversion configuration directory.

            repopath (str):
                The path to the repository.

            username (str, optional):
                The username for the repository.

            password (str, optional):
                The password for the repository.
        """
        self.repopath = repopath

    def set_ssl_server_trust_prompt(self, cb):
        """Set a function for verifying a SSL certificate.

        Args:
            cb (callable):
                The function to call for verifying SSL certificates.
        """
        raise NotImplementedError

    def get_file(self, path, revision=HEAD):
        """Return the contents of a file from the repository.

        This attempts to return the raw binary contents of a file from the
        repository, given a file path and revision.

        Args:
            path (str):
                The path to the file in the repository.

            revision (reviewboard.scmtools.core.Revision, optional):
                The revision to fetch. Subclasses should default this to
                :py:data:`HEAD`.

            *args (tuple, unused):
                Additional unused positional arguments.

            **kwargs (dict, unused):
                Additional unused keyword arguments.

        Returns:
            bytes:
            The returned file contents.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be found in the repository.

            reviewboard.scmtools.errors.InvalidRevisionFormatError:
                The ``revision`` argument was in an invalid format.

            reviewboard.scmtools.errors.SCMError:
                An unexpected error was encountered with the repository.
        """
        raise NotImplementedError

    def get_keywords(self, path, revision=HEAD):
        """Return a space-separated list of SVN keywords for a given path.

        Args:
            path (str):
                The path to the file or directory.

            revision (str):
                The revision containing the keywords.

        Returns:
            str:
            The resulting keywords.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error was encountered with the repository.

                This may be a more specific subclass.
        """
        raise NotImplementedError

    def get_log(self, path, start=None, end=None, limit=None,
                discover_changed_paths=False, limit_to_path=False):
        """Return log entries at the specified path.

        The log entries will appear ordered from most recent to least,
        with ``start`` being the most recent commit in the range.

        Args:
            path (str):
                The path to limit log entries to.

            start (str, optional):
                The start revision for the log.

                If not specified, clients must default this to "HEAD".

            end (str, optional):
                The end revision for the log.

                If not specified, clients must default this to "1".

            limit (int, optional):
                The maximum number of entries to return.

            discover_changed_paths (bool, optional):
                Whether to include information on changed paths in the
                results.

            limit_to_path (bool, optional):
                Limits results to ``path`` without factoring in history from
                any branch operations.

        Returns:
            list of SVNLogEntry:
            The list of resulting log entries.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error was encountered with the repository.

                This may be a more specific subclass.
        """
        raise NotImplementedError

    def list_dir(self, path):
        """Return the directory contents of the specified path.

        The result will be an ordered dictionary of contents, mapping
        filenames or directory names with directory information.

        Args:
            path (str):
                The directory path.

        Returns:
            collections.OrderedDict:
            A dictionary mapping directory names as strings to
            :py:class:`SVNDirEntry` information.
        """
        raise NotImplementedError

    def diff(self, revision1, revision2, path=None):
        """Return a diff between two revisions.

        The diff will contain the differences between the two revisions,
        and may optionally be limited to a specific path.

        Args:
            revision1 (str):
                The first revision in the range.

            revision2 (str):
                The second revision in the range.

            path (str, optional):
                An optional path to limit the diff to.

        Returns:
            bytes:
            The resulting diff contents.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error was encountered with the repository.

                This may be a more specific subclass.
        """
        raise NotImplementedError

    @property
    def repository_info(self):
        """Metadata about the repository.

        This is a dictionary containing the following keys:

        ``uuid`` (:py:class:`unicode`):
            The UUID of the repository.

        ``root_url`` (:py:class:`unicode`):
            The root URL of the configured repository.

        ``url`` (:py:class:`unicoe`):
            The full URL of the configured repository.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error was encountered with the repository.

                This may be a more specific subclass.
        """
        raise NotImplementedError

    def normalize_path(self, path):
        """Normalize a path to a file/directory for a request to Subversion.

        If the path is an absolute path beginning at the base of the
        repository, it will be returned as-is. Otherwise, it will be appended
        onto the repository path, with any leading ``/`` characters on the
        path removed.

        If appending the path, care will be taken to quote special characters
        like a space, ``#``, or ``?``, in order to ensure that they're not
        mangled. There are many characters Subversion does consider valid that
        would normally be quoted, so this isn't true URL quoting.

        All trailing ``/`` characters will also be removed.

        Args:
            path (unicode):
                The path to normalize.

        Returns:
            unicode:
            The normalized path.
        """
        if path.startswith(self.repopath):
            norm_path = path
        else:
            # Some important notes for the quoting below:
            #
            # 1) Subversion requires that we operate off of a URI-based
            #    repository path in order for file lookups to at all work, so
            #    we can be sure we're building a URI here. That means we're
            #    safe to quote.
            #
            # 2) This is largely being mentioned because the original
            #    contribution to fix a lookup issue here with special
            #    characters was written to be compatible with local file
            #    paths. Support for that is a pretty common assumption, but
            #    is unnecessary, so the code here is safe.
            #
            # 3) We can't rely on urllib's standard quoting behavior.
            #    completely. Subversion has a specific table of characters
            #    that must be quoted, and ones that can't be. There is enough
            #    we can leverage from urlquote's own table, but we need to
            #    mark several more as safe.
            #
            #    See the "svn_uri_char_validity" look up table and notes here:
            #
            #    https://github.com/apache/subversion/blob/trunk/subversion/libsvn_subr/path.c
            #
            # 4) file:// URLs don't allow non-printable characters (character
            #    codes < 32), while non-file:// URLs do. We don't want to
            #    trigger issues in Subversion (earlier versions assume this
            #    is our responsibility), so we validate here.
            #
            # 5) Modern Subversion seems to handle its own normalization now,
            #    from what we can tell. That might not always be true, though,
            #    and we need to support older versions, so we'll continue to
            #    maintain this going forward.
            if self.repopath.startswith('file:'):
                # Validate that this doesn't have any unprintable ASCII
                # characters or older versions of Subversion will throw a
                # fit.
                for c in path:
                    if 0 <= ord(c) < 32:
                        raise SCMError(
                            _('Invalid character code %(code)s found in '
                              'path %(path)r.')
                            % {
                                'code': ord(c),
                                'path': path,
                            })

            norm_path = '%s/%s' % (
                self.repopath,
                quote(path.lstrip('/'), safe="!$&'()*+,'-./:=@_~")
            )

        return norm_path.rstrip('/')

    def accept_ssl_certificate(self, path, on_failure=None):
        """Attempt to accept a SSL certificate.

        If the repository uses SSL, this method is used to determine whether
        the SSL certificate can be automatically accepted.

        If the cert cannot be accepted, the ``on_failure`` callback
        is executed.

        Args:
            path (str):
                The repository path.

            on_failure (callable, optional):
                A function to call if the certificate could not be accepted.

        Returns:
            dict:
            Serialized information on the certificate.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                There was an error accepting the certificate.
        """
        raise NotImplementedError
