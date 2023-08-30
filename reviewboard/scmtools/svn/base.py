"""Base backend support for Subversion clients."""

from __future__ import annotations

from abc import ABC, abstractmethod, abstractproperty
from contextlib import contextmanager
from typing import (Any, Callable, Dict, Iterator, Optional, Sequence,
                    TYPE_CHECKING, Tuple)
from urllib.parse import quote

from django.utils.translation import gettext as _
from typing_extensions import Final, NotRequired, TypeAlias, TypedDict

from reviewboard.scmtools.core import HEAD
from reviewboard.scmtools.errors import SCMError
from reviewboard.scmtools.svn import RawSSLTrustDict

if TYPE_CHECKING:
    from collections import OrderedDict
    from datetime import datetime
    from reviewboard.scmtools.core import RevisionID


class SVNDirEntry(TypedDict):
    """Information on an entry in a directory.

    Version Added:
        6.0
    """

    #: The path to the entry.
    #:
    #: Type:
    #:     str
    path: str

    #: The revision when this was created.
    #:
    #: Type:
    #:     str
    created_rev: str


class SVNLogEntry(TypedDict):
    """Information on a log entry from Subversion.

    The log entry can cover a file, directory, or property.

    Version Added:
        6.0
    """

    #: The revision of the entry.
    #:
    #: Type:
    #:     bytes or str
    revision: str

    #: The author of the entry.
    #:
    #: Type:
    #:     bytes or str
    author: str

    #: The date of the entry.
    #:
    #: Type:
    #:     datetime.datetime
    date: NotRequired[datetime]

    #: The commit message.
    #:
    #: Type:
    #:     bytes or str
    message: str


class SVNRepositoryInfoDict(TypedDict):
    """Information about a Subversion repository.

    This provides information available to consumers of the API.

    Version Added:
        6.0
    """

    #: The root URL of the configured repository.
    #:
    #: Type:
    #:     str
    root_url: str

    #: The full URL of the configured repository.
    #:
    #: Type:
    #:     str
    url: str

    #: The UUID of the repository.
    #:
    #: Type:
    #:     str
    uuid: str


class Client(ABC):
    """Base class for a Subversion client."""

    #: The default start revision for log entries.
    LOG_DEFAULT_START: Final[str] = 'HEAD'

    #: The default end revision for log entries.
    LOG_DEFAULT_END: Final[str] = '1'

    #: An optional Python module required for Subversion support.
    required_module: Optional[str] = None

    ######################
    # Instance variables #
    ######################

    #: The path to the Subversion configuration directory.
    #:
    #: Type:
    #:     str
    config_dir: str

    #: The path to the repository.
    #:
    #: Type:
    #:     str
    repopath: str

    def __init__(
        self,
        config_dir: str,
        repopath: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
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
        self.config_dir = config_dir
        self.repopath = repopath

    @contextmanager
    def communicate(self) -> Iterator[None]:
        """Context manager for any code communicating with Subversion.

        This should be used any time code is ready to perform an operation
        on a Subversion repository. It will catch any errors from the client
        that need to be processed and allow the client to normalize them.

        Version Added:
            6.0

        Yields:
            The communication operation will run in this context.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error communicating with Subversion.
        """
        try:
            with self.communicate_hook():
                yield
        except SCMError:
            # This is already an explicit error. Raise this as normal.
            raise
        except Exception as e:
            # Allow the client to convert the error to a normalized form.
            raise self.normalize_error(e) from e

    @contextmanager
    def communicate_hook(self) -> Iterator[None]:
        """Hook for running a communication task.

        This is intended for unit tests only. All exceptions are
        pass-through.

        Version Added:
            6.0

        Yields:
            The communication operation will run in this context.
        """
        yield

    @abstractmethod
    def normalize_error(
        self,
        e: Exception,
    ) -> Exception:
        """Normalize an exception from the client.

        This will process the exception information and return an exception
        suitable for forwarding to the backend, as documented below.

        Args:
            e (Exception):
                The exception to normalize.

        Returns:
            Exception:
            The normalized exception.

        Raises:
            reviewboard.scmtools.errors.AuthenticationError:
                An authentication error communicating with the repository.

            reviewboard.scmtools.errors.SCMError:
                A general error communicating with the repository.
        """
        raise NotImplementedError

    @abstractmethod
    def set_ssl_server_trust_prompt(
        self,
        cb: SSLServerTrustPromptFunc,
    ) -> None:
        """Set a function for verifying a SSL certificate.

        Args:
            cb (callable):
                The function to call for verifying SSL certificates.
        """
        raise NotImplementedError

    @abstractmethod
    def get_file(
        self,
        path: str,
        revision: RevisionID = HEAD,
    ) -> bytes:
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

    @abstractmethod
    def get_keywords(
        self,
        path: str,
        revision: RevisionID = HEAD,
    ) -> str:
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

    @abstractmethod
    def get_log(
        self,
        path: str,
        *,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
        discover_changed_paths: bool = False,
        limit_to_path: bool = False,
    ) -> Sequence[SVNLogEntry]:
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

    @abstractmethod
    def list_dir(
        self,
        path: str,
    ) -> OrderedDict[str, SVNDirEntry]:
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

    @abstractmethod
    def diff(
        self,
        revision1: str,
        revision2: str,
        path: Optional[str] = None,
    ) -> bytes:
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

    @abstractproperty
    def repository_info(self) -> SVNRepositoryInfoDict:
        """Metadata about the repository.

        See :py:class:`SVNRepositoryInfoDict` for contents.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                An error was encountered with the repository.

                This may be a more specific subclass.
        """
        raise NotImplementedError

    def normalize_path(
        self,
        path: str,
    ) -> str:
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
            path (str):
                The path to normalize.

        Returns:
            str:
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

    @abstractmethod
    def accept_ssl_certificate(
        self,
        path: str,
        on_failure: Optional[AcceptCertificateFunc] = None,
    ) -> Dict[str, Any]:
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


#: Type for a callback handle for accepting SSL certificates.
#:
#: Version Added:
#:     6.0
AcceptCertificateFunc: TypeAlias = Callable[
    [Client, Exception, str, Dict[str, Any]],
    None,
]


#: Type for a callback handle for prompting for SSL trust information.
#:
#: Version Added:
#:     6.0
SSLServerTrustPromptFunc: TypeAlias = Callable[
    [RawSSLTrustDict],
    Tuple[bool, int, bool],
]
