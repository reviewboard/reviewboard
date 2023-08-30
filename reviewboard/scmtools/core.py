"""Data structures and classes for defining and using SCMTools."""

from __future__ import annotations

import base64
import logging
import os
import subprocess
from typing import (Any, Dict, List, Mapping, Optional, Sequence,
                    TYPE_CHECKING, Type, Tuple, Union)
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request as URLRequest, urlopen

import importlib_metadata
from django.utils.encoding import force_bytes, force_str
from django.utils.translation import gettext_lazy as _
from djblets.util.properties import TypedProperty
from typing_extensions import TypeAlias

from reviewboard.scmtools.errors import (AuthenticationError,
                                         FileNotFoundError,
                                         SCMError)
from reviewboard.ssh import utils as sshutils
from reviewboard.ssh.errors import SSHAuthenticationError

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
    from django.http import HttpRequest
    from django.utils.functional import _StrOrPromise
    from djblets.util.typing import JSONDict
    from reviewboard.diffviewer.parser import BaseDiffParser
    from reviewboard.scmtools.certs import Certificate
    from reviewboard.scmtools.forms import (BaseSCMToolAuthForm,
                                            BaseSCMToolRepositoryForm)
    from reviewboard.scmtools.models import Repository
    from reviewboard.site.models import LocalSite


logger = logging.getLogger(__name__)


#: An alias for a TypedProperty taking a bytes value or None.
#:
#: Version Added:
#:     6.0
_BytesProperty: TypeAlias = TypedProperty[Optional[bytes], Optional[bytes]]


#: An alias for a TypedProperty taking an int value or None.
#:
#: Version Added:
#:     6.0
_IntProperty: TypeAlias = TypedProperty[Optional[int], Optional[int]]


#: An alias for a TypedProperty taking a str value or None.
#:
#: Version Added:
#:     6.0
_StrProperty: TypeAlias = TypedProperty[Optional[str], Optional[str]]


#: An alias for a TypedProperty taking a str value.
#:
#: Version Added:
#:     6.0
_StrRequiredProperty: TypeAlias = TypedProperty[str, str]


class ChangeSet:
    """A server-side changeset.

    This represents information on a server-side changeset, which tracks
    the information on a commit and modified files for some types of
    repositories (such as Perforce).

    Not all data may be provided by the server.
    """

    ######################
    # Instance variables #
    ######################

    #: The destination branch.
    #:
    #: Type:
    #:     str
    branch: _StrProperty = TypedProperty(str)

    #: A list of bug IDs that were closed by this change.
    #:
    #: Type:
    #:     list of str
    bugs_closed: List[str]

    #: The changeset number/ID.
    #:
    #: Type:
    #:     int
    changenum: _IntProperty = TypedProperty(int)

    #: The description of the change.
    #:
    #: Type:
    #:     str
    description: _StrProperty = TypedProperty(str)

    #: Extra data to store in the draft.
    #:
    #: These may map to custom fields.
    #:
    #: Version Added:
    #:     5.0.5
    extra_data: JSONDict

    #: A list of filenames added/modified/deleted by the change.
    #:
    #: Type:
    #:     list of str
    files: List[str]

    #: Whether or not the change is pending (not yet committed).
    #:
    #: Type:
    #:     bool
    pending: bool

    #: The summary of the change.
    #:
    #: Type:
    #:     str
    summary: _StrProperty = TypedProperty(str)

    #: Testing information for the change.
    #:
    #: Type:
    #:     str
    testing_done: _StrProperty = TypedProperty(str)

    #: The username of the user who made the change.
    #:
    #: Type:
    #:     str
    username: _StrProperty = TypedProperty(str)

    def __init__(self):
        """Initialize the changeset."""
        self.branch = ''
        self.bugs_closed = []
        self.changenum = None
        self.description = ''
        self.extra_data = {}
        self.files = []
        self.pending = False
        self.summary = ''
        self.testing_done = ''
        self.username = ''


class Revision:
    """A revision in a diff or repository.

    This represents a specific revision in a tree, or a specialized indicator
    that can have special meaning.
    """

    ######################
    # Instance variables #
    ######################

    #: The name/ID of the revision.
    #:
    #: Type:
    #:     str
    name: _StrRequiredProperty = TypedProperty(str, allow_none=False)

    def __init__(
        self,
        name: str,
    ) -> None:
        """Initialize the Revision.

        Args:
            name (str):
                The name of the revision. This may be a special name (which
                should be in all-uppercase) or a revision ID.

        Raises:
            TypeError:
                The provided name was not a Unicode string.
        """
        self.name = name

    def __bytes__(self) -> bytes:
        """Return a byte string representation of the revision.

        This is equivalent to fetching :py:attr:`name` and encoding to UTF-8.

        Returns:
            bytes:
            The name/ID of the revision.
        """
        return self.name.encode('utf-8')

    def __str__(self) -> str:
        """Return a Unicode string representation of the revision.

        This is equivalent to fetching :py:attr:`name`.

        Returns:
            str:
            The name/ID of the revision.
        """
        return self.name

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        """Return whether this revision equals another.

        Args:
            other (Revision):
                The revision to compare to.

        Returns:
            bool:
            ``True`` if the two revisions are equal. ``False`` if they are
            not equal.
        """
        return self.name == force_str(other)

    def __ne__(
        self,
        other: Any,
    ) -> bool:
        """Return whether this revision is not equal to another.

        Args:
            other (Revision):
                The revision to compare to.

        Returns:
            bool:
            ``True`` if the two revisions are not equal. ``False`` if they are
            equal.
        """
        return self.name != force_str(other)

    def __repr__(self) -> str:
        """Return a string representation of this revision.

        Returns:
            str:
            The string representation.
        """
        return '<Revision: %s>' % self.name


class Branch:
    """A branch in a repository."""

    ######################
    # Instance variables #
    ######################

    #: The latest commit ID on the branch.
    #:
    #: Type:
    #:     str
    commit: _StrProperty = TypedProperty(str)

    #: Whether or not this is the default branch for the repository.
    #:
    #: One (and only one) branch in a list of returned branches should
    #: have this set to ``True``.
    #:
    #: Type:
    #:     bool
    default: bool

    #: The ID of the branch.
    #:
    #: Type:
    #:     str
    id: _StrRequiredProperty = TypedProperty(str, allow_none=False)

    #: The name of the branch.
    #:
    #: Type:
    #:     str
    name: _StrProperty = TypedProperty(str)

    def __init__(
        self,
        id: str,
        name: Optional[str] = None,
        commit: str = '',
        default: bool = False,
    ) -> None:
        """Initialize the branch.

        Args:
            id (str):
                The ID of the branch.

            name (str, optional):
                The name of the branch. If not specified, this will default
                to the ID.

            commit (str, optional):
                The latest commit ID on the branch.

            default (bool, optional):
                Whether or not this is the default branch for the repository.
        """
        self.id = id
        self.name = name or self.id
        self.commit = commit
        self.default = default

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        """Return whether this branch is equal to another branch.

        Args:
            other (Branch):
                The branch to compare to.

        Returns:
            bool:
            ``True`` if the two branches are equal. ``False`` if they are not.
        """
        return (isinstance(other, Branch) and
                self.id == other.id and
                self.name == other.name and
                self.commit == other.commit and
                self.default == other.default)

    def __repr__(self) -> str:
        """Return a string representation of this branch.

        Returns:
            str:
            The string representation.
        """
        return ('<Branch %s (name=%s; commit=%s: default=%r)>'
                % (self.id, self.name, self.commit, self.default))


class Commit:
    """A commit in a repository."""

    ######################
    # Instance variables #
    ######################

    #: The name or username of the author who made the commit.
    #:
    #: Type:
    #:     str
    author_name: _StrProperty = TypedProperty(str)

    #: The timestamp of the commit as a string in ISO 8601 format.
    #:
    #: Type:
    #:     str
    date: _StrProperty = TypedProperty(str)

    #: The contents of the commit's diff.
    #:
    #: This may be ``None``, depending on how the commit is fetched.
    diff: _BytesProperty = TypedProperty(bytes)

    #: The ID of the commit.
    #:
    #: This should be its SHA/revision.
    #:
    #: Type:
    #:     str
    id: _StrProperty = TypedProperty(str)

    #: The commit message.
    #:
    #: Type:
    #:     str
    message: _StrProperty = TypedProperty(str)

    #: The ID of the commit's parent.
    #:
    #: This should be its SHA/revision. If this is the first commit, this
    #: should be ``None`` or an empty string.
    #:
    #: Type:
    #:     str
    parent: _StrProperty = TypedProperty(str)

    def __init__(
        self,
        author_name: str = '',
        id: str = '',
        date: str = '',
        message: str = '',
        parent: str = '',
        diff: Optional[bytes] = None,
    ) -> None:
        """Initialize the commit.

        All arguments are optional, and can be set later.

        Args:
            author_name (str, optional):
                The name of the author who made this commit. This should be
                the full name, if available, but can be the username or other
                identifier.

            id (str, optional):
                The ID of the commit. This should be its SHA/revision.

            date (str, optional):
                The timestamp of the commit as a string in ISO 8601 format.

            message (str, optional):
                The commit message.

            parent (str, optional):
                The ID of the commit's parent. This should be its SHA/revision.

            diff (bytes, optional):
                The contents of the commit's diff.
        """
        self.author_name = author_name
        self.id = id
        self.date = date
        self.message = message
        self.parent = parent

        # This field is only used when we're actually fetching the commit from
        # the server to create a new review request, and isn't part of the
        # equality test.
        self.diff = diff

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        """Return whether this commit is equal to another commit.

        Args:
            other (Commit):
                The commit to compare to.

        Returns:
            bool:
            ``True`` if the two commits are equal. ``False`` if they are not.
        """
        return (isinstance(other, Commit) and
                self.author_name == other.author_name and
                self.id == other.id and
                self.date == other.date and
                self.message == other.message and
                self.parent == other.parent)

    def __repr__(self) -> str:
        """Return a string representation of this commit.

        Returns:
            str:
            The string representation.
        """
        return ('<Commit %r (author=%s; date=%s; parent=%r)>'
                % (self.id, self.author_name, self.date, self.parent))

    def split_message(self) -> Tuple[str, str]:
        """Return a split version of the commit message.

        This will separate the commit message into a summary and body, if
        possible.

        Returns:
            tuple:
            A 2-tuple containing:

            Tuple:
                0 (str):
                    The summary of the commit.

                1 (str):
                    The commit message.

            If the commit message is only a single line, both items in the
            tuple will be that line.
        """
        message = self.message or ''
        parts = message.split('\n', 1)
        summary = parts[0]

        try:
            message = parts[1]
        except IndexError:
            # If the description is only one line long, pass through--'message'
            # will still be set to what we got from get_change, and will show
            # up as being the same thing as the summary.
            pass

        return summary, message


class FileLookupContext:
    """Information available to aid in looking up files from a repository.

    This is a container for several pieces of data that a SCM may need in
    order to look up content or details about a file from a repository.

    Version Added:
        4.0.5
    """

    ######################
    # Instance variables #
    ######################

    #: The ID of the commit that the file was changed in.
    #:
    #: This may be ``None``. The contents and interpretation are dependent on
    #: the of the repository.
    base_commit_id: Optional[str]

    #: Metadata stored about the parsed commit from the diff.
    #:
    #: This is generally the data in :py:attr:`DiffCommit.extra_data
    #: <reviewboard.diffviewer.models.diffcommit.DiffCommit.extra_data>`
    #: or :py:attr:`ParsedDiffChange.extra_data
    #: <reviewboard.diffviewer.parser.ParsedDiffChange.extra_data>`.
    commit_extra_data: JSONDict

    #: General metadata stored about the parsed diff.
    #:
    #: This is generally the data in :py:attr:`DiffSet.extra_data
    #: <reviewboard.diffviewer.models.diffset.DiffSet.extra_data>`
    #: or :py:attr:`ParsedDiff.extra_data
    #: <reviewboard.diffviewer.parser.ParsedDiff.extra_data>`.
    diff_extra_data: JSONDict

    #: General metadata stored about the parsed file from the diff.
    #:
    #: This is generally the data in :py:attr:`FileDiff.extra_data
    #: <reviewboard.diffviewer.models.filediff.FileDiff.extra_data>`
    #: or :py:attr:`ParsedDiffFile.extra_data
    #: <reviewboard.diffviewer.parser.ParsedDiffFile.extra_data>`.
    file_extra_data: JSONDict

    #: The HTTP request from the client that triggered the file lookup.
    #:
    #: This may be ``None``.
    request: Optional[HttpRequest]

    #: The user triggering the repository lookup.
    #:
    #: This is **not** the user that's communicating with the repository.
    user: Optional[Union[AbstractBaseUser, AnonymousUser]]

    def __init__(
        self,
        request: Optional[HttpRequest] = None,
        user: Optional[Union[AbstractBaseUser, AnonymousUser]] = None,
        base_commit_id: Optional[str] = None,
        diff_extra_data: JSONDict = {},
        commit_extra_data: JSONDict = {},
        file_extra_data: JSONDict = {},
    ) -> None:
        """Initialize the context.

        Args:
            request (django.http.HttpRequest, optional):
                The HTTP request from the client that triggered the file
                lookup. This may be ``None``.

            user (django.contrib.auth.models.User, optional):
                The user triggering the repository lookup. This defaults
                to the user from ``request``.

                This is **not** the user that's communicating with the
                repository.

            base_commit_id (str, optional):
                The ID of the commit that the file was changed in. This may be
                ``None``. The contents and interpretation are dependent on the
                type of the repository.

            diff_extra_data (dict, optional):
                General metadata stored about the parsed diff.

                This is generally the data in :py:attr:`DiffSet.extra_data
                <reviewboard.diffviewer.models.diffset.DiffSet.extra_data>`
                or :py:attr:`ParsedDiff.extra_data
                <reviewboard.diffviewer.parser.ParsedDiff.extra_data>`.

            commit_extra_data (dict, optional):
                Metadata stored about the parsed commit from the diff.

                This is generally the data in :py:attr:`DiffCommit.extra_data
                <reviewboard.diffviewer.models.diffcommit.DiffCommit.
                extra_data>` or :py:attr:`ParsedDiffChange.extra_data
                <reviewboard.diffviewer.parser.ParsedDiffChange.extra_data>`.

            file_extra_data (dict, optional):
                General metadata stored about the parsed file from the diff.

                This is generally the data in :py:attr:`FileDiff.extra_data
                <reviewboard.diffviewer.models.filediff.FileDiff.extra_data>`
                or :py:attr:`ParsedDiffFile.extra_data
                <reviewboard.diffviewer.parser.ParsedDiffFile.extra_data>`.

        Raises:
            TypeError:
                A provided attribute is of an incorrect type.
        """
        if (base_commit_id is not None and
            not isinstance(base_commit_id, str)):
            raise TypeError(
                '"base_commit_id" must be a Unicode string, not %s'
                % type(base_commit_id))

        if user is None and request is not None:
            user = getattr(request, 'user', None)

        self.base_commit_id = base_commit_id
        self.commit_extra_data = commit_extra_data
        self.diff_extra_data = diff_extra_data
        self.file_extra_data = file_extra_data
        self.request = request
        self.user = user


#: Latest revision in the tree (or branch).
HEAD = Revision('HEAD')

#: Unknown revision.
#:
#: This is used to indicate that a revision could not be found or parsed.
UNKNOWN = Revision('UNKNOWN')

#: Revision representing a new file (prior to entering the repository).
PRE_CREATION = Revision('PRE-CREATION')

#: A type indicating either a revision constant or repository-specific ID.
#:
#: Version Added:
#:     5.0.5
RevisionID: TypeAlias = Union[Revision, str]


class _SCMToolIDProperty(str):
    """A property that automatically determines the ID for an SCMTool.

    This is used for SCMTools that don't explicitly specify a
    :py:attr:`SCMTool.scmtool_id` value. It will attempt to find a matching
    Python EntryPoint for the class and use its registration key as the ID.

    Version Added:
        3.0.16
    """

    _scmtool_ids_by_class_names: Dict[str, str] = {}

    def __get__(
        self,
        owner_self,
        owner_cls,
    ) -> Optional[str]:
        """Return the ID for the SCMTool.

        Args:
            owner_self (SCMTool, ignored):
                The instance of the tool, if requesting the value on an
                instance.

            owner_cls (type):
                The subclass of :py:class:`SCMTool`.

        Returns:
            str:
            The resulting SCMTool ID.

        Raises:
            ValueError:
                The ID could not be determined, as it was not registered
                by a known Python EntryPoint.
        """
        if not _SCMToolIDProperty._scmtool_ids_by_class_names:
            eps = importlib_metadata.entry_points(group='reviewboard.scmtools')
            _SCMToolIDProperty._scmtool_ids_by_class_names = {
                '%s.%s' % (ep.module_name, ep.attrs[0]): force_str(ep.name)
                for ep in eps
            }

        if owner_cls is SCMTool:
            return None

        key = '%s.%s' % (owner_cls.__module__, owner_cls.__name__)

        try:
            return _SCMToolIDProperty._scmtool_ids_by_class_names[key]
        except KeyError:
            raise ValueError(
                _('Unable to determine an SCMTool ID for %r. You must set '
                  '%s.scmtool_id to a unique value.')
                % (owner_cls, owner_cls.__name__))


class SCMTool:
    """A backend for talking to a source code repository.

    This is responsible for handling all the communication with a repository
    and working with data provided by a repository. This includes validating
    repository configuration, fetching file contents, returning log information
    for browsing commits, constructing a diff parser for the repository's
    supported diff format(s), and more.
    """

    #: A unique identifier for the SCMTool.
    #:
    #: If not provided, this will be based on its key in the
    #: ``reviewboard.scmtools`` Python EntryPoint. This will become a required
    #: attribute in a future version.
    #:
    #: Version Added:
    #:     3.0.16
    scmtool_id: str = _SCMToolIDProperty()

    #: The human-readable name of the SCMTool.
    #:
    #: Users will see this when they go to select a repository type. Some
    #: examples would be "Subversion" or "Perforce".
    name: Optional[str] = None

    #: Whether or not the SCMTool supports review requests with history.
    supports_history: bool = False

    #: Whether or not commits in this SCMTool require the committer fields.
    commits_have_committer: bool = False

    #: Whether server-side pending changesets are supported.
    #:
    #: These are used by some types of repositories to track what changes
    #: are currently open by what developer, what files they touch, and what
    #: the commit message is. Basically, they work like server-side drafts for
    #: commits.
    #:
    #: If ``True``, Review Board will allow updating the review request's
    #: information from the pending changeset, and will indicate in the UI
    #: if it's pending or submitted.
    supports_pending_changesets: bool = False

    #: Whether existing commits can be browsed and posted for review.
    #:
    #: If ``True``, the New Review Request page and API will allow for
    #: browsing and posting existing commits and their diffs for review.
    supports_post_commit: bool = False

    #: Whether custom URL masks can be defined to fetching file contents.
    #:
    #: Some systems (such as Git) have no way of accessing an individual file
    #: in a repository over a network without having a complete up-to-date
    #: checkout accessible to the Review Board server. For those, Review Board
    #: can offer a field for specifying a URL mask (a URL with special strings
    #: acting as a template) that will be used when pulling down the contents
    #: of a file referenced in a diff.
    #:
    #: If ``True``, this field will be shown in the repository configuration.
    #: It's up to the SCMTool to handle and parse the value.
    supports_raw_file_urls: bool = False

    #: Whether ticket-based authentication is supported.
    #:
    #: Ticket-based authentication is an authentication method where the
    #: SCMTool requests an authentication ticket from the repository, in order
    #: to access repository content. For these setups, the SCMTool must handle
    #: determining when it needs a new ticket and requesting it, generally
    #: based on the provided username and password.
    #:
    #: If ``True``, an option will be shown for enabling this when configuring
    #: the repository. It's up to the SCMTool to make use of it.
    supports_ticket_auth: bool = False

    #: Whether filenames in diffs are stored using absolute paths.
    #:
    #: This is used when uploading and validating diffs to determine if the
    #: user must supply the base path for a diff. Some types of SCMs (such as
    #: Subversion) store relative paths in diffs, requiring additional
    #: information in order to generate an absolute path for lookups.
    #:
    #: By default, this is ``False``. Subclasses must override this if their
    #: diff formats list absolute paths.
    diffs_use_absolute_paths: bool = False

    #: Whether diff files use a defined commit ID as file revisions.
    #:
    #: This is used for SCMs where diffs use commit IDs to look up file
    #: contents rather than individual revisions, and those commit IDs are
    #: defined as metadata in the diff without necessarily being listed
    #: along with each file.
    #:
    #: When enabled, diff parsing will expect to find parent commit IDs
    #: in the diff, and those parent commit IDs will be used if the parser
    #: doesn't find a suitable revision associated with an individual file.
    #: This particularly applies when a file is present in a diff but not
    #: in a parent diff, and the parent diff's parent commit ID needs to be
    #: used to look up the file.
    #:
    #: By default, this is ``False``. Subclasses must override this is if
    #: they need this behavior.
    #:
    #: Version Added:
    #:     4.0.5
    diffs_use_commit_ids_as_revisions: bool = False

    #: Whether this prefers the Mirror Path value for communication.
    #:
    #: This will affect which field the repository configuration form will
    #: use for repository validation and for accepting certificates.
    #:
    #: This should generally **not** be set by new SCMTools. It exists for
    #: backwards-compatibility with Perforce.
    #:
    #: Version Added:
    #:     3.0.18
    prefers_mirror_path: bool = False

    #: Overridden help text for the configuration form fields.
    #:
    #: This allows the form fields to have custom help text for the SCMTool,
    #: providing better guidance for configuration.
    field_help_text: Dict[str, _StrOrPromise] = {
        'path': _('The path to the repository. This will generally be the URL '
                  'you would use to check out the repository.'),
    }

    #: A dictionary containing lists of dependencies needed for this SCMTool.
    #:
    #: This should be overridden by subclasses that require certain external
    #: modules or binaries. It has two keys: ``executables`` and ``modules``.
    #: Each map to a list of names.
    #:
    #: The list of Python modules go in ``modules``, and must be valid,
    #: importable modules. If a module is not available, the SCMTool will
    #: be disabled.
    #:
    #: The list of executables shouldn't contain a file extensions (e.g.,
    #: ``.exe``), as Review Board will automatically attempt to use the
    #: right extension for the platform.
    dependencies: Dict[str, List[str]] = {
        'executables': [],
        'modules': [],
    }

    #: A custom form used to collect authentication details.
    #:
    #: This allows subclasses to remove, change, or augment the standard
    #: fields for collecting a repository's username and password.
    #:
    #: Version Added:
    #:     3.0.16
    auth_form: Optional[Type[BaseSCMToolAuthForm]] = None

    #: A custom form used to collect repository details.
    #:
    #: This allows subclasses to remove, change, or augment the standard
    #: fields for collecting a repository's path, mirror path, and other
    #: common information.
    #:
    #: Version Added:
    #:     3.0.16
    repository_form: Optional[Type[BaseSCMToolRepositoryForm]] = None

    ######################
    # Instance variables #
    ######################

    #: The repository owning an instance of this SCMTool.
    repository: Repository

    def __init__(
        self,
        repository: Repository,
    ) -> None:
        """Initialize the SCMTool.

        This will be initialized on demand, when first needed by a client
        working with a repository. It will generally be bound to the lifetime
        of the repository instance.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository owning this SCMTool.
        """
        self.repository = repository

    def get_file(
        self,
        path: str,
        revision: RevisionID = HEAD,
        base_commit_id: Optional[str] = None,
        context: Optional[FileLookupContext] = None,
        **kwargs,
    ) -> bytes:
        """Return the contents of a file from a repository.

        This attempts to return the raw binary contents of a file from the
        repository, given a file path and revision.

        It may also take a base commit ID, which is the ID (SHA or revision
        number) of a commit changing or introducing the file. This may differ
        from the revision for some types of repositories, where different IDs
        are used for a file content revision and a commit revision.

        Subclasses must implement this.

        Version Changed:
            4.0.5:
            Added ``context``, which deprecates ``base_commit_id`` and adds
            new capabilities for file lookups.

        Args:
            path (str):
                The path to the file in the repository.

            revision (Revision, optional):
                The revision to fetch. Subclasses should default this to
                :py:data:`HEAD`.

            base_commit_id (str, optional):
                The ID of the commit that the file was changed in. This may
                not be provided, and is dependent on the type of repository.

                Deprecated:
                    4.0.5:
                    This will still be provided, but implementations should
                    use :py:attr:`FileLookupContext.base_commit_id`` instead
                    when running on Review Board 4.0.5+.

            context (FileLookupContext, optional):
                Extra context used to help look up this file.

                This contains information about the HTTP request, requesting
                user, and parsed diff information, which may be useful as
                part of the repository lookup process.

                This is always provided on Review Board 4.0.5 and higher.
                Implementations should be careful to validate the presence
                and values of any metadata stored within this.

                Version Added:
                    4.0.5

            **kwargs (dict):
                Additional keyword arguments. This is not currently used, but
                is available for future expansion.

        Returns:
            bytes:
            The returned file contents.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be found in the repository.

            reviewboard.scmtools.errors.InvalidRevisionFormatError:
                The ``revision`` or ``base_commit_id`` arguments were in an
                invalid format.
        """
        raise NotImplementedError

    def file_exists(
        self,
        path: str,
        revision: RevisionID = HEAD,
        base_commit_id: Optional[str] = None,
        context: Optional[FileLookupContext] = None,
        **kwargs,
    ) -> bool:
        """Return whether a particular file exists in a repository.

        Like :py:meth:`get_file`, this may take a base commit ID, which is the
        ID (SHA or revision number) of a commit changing or introducing the
        file. This depends on the type of repository, and may not be provided.

        Subclasses should only override this if they have a more efficient
        way of checking for a file's existence than fetching the file contents.

        Version Changed:
            4.0.5:
            Added ``context``, which deprecates ``base_commit_id`` and adds
            new capabilities for file lookups.

        Args:
            path (str):
                The path to the file in the repository.

            revision (Revision, optional):
                The revision to fetch. Subclasses should default this to
                :py:data:`HEAD`.

            base_commit_id (str, optional):
                The ID of the commit that the file was changed in. This may
                not be provided, and is dependent on the type of repository.

                Deprecated:
                    4.0.5:
                    This will still be provided, but implementations should
                    use :py:attr:`FileLookupContext.base_commit_id`` instead
                    when running on Review Board 4.0.5+.

            context (FileLookupContext, optional):
                Extra context used to help look up this file.

                This contains information about the HTTP request, requesting
                user, and parsed diff information, which may be useful as
                part of the repository lookup process.

                This is always provided on Review Board 4.0.5 and higher.
                Implementations should be careful to validate the presence
                and values of any metadata stored within this.

                Version Added:
                    4.0.5

            **kwargs (dict):
                Additional keyword arguments. This is not currently used, but
                is available for future expansion.

        Returns:
            bool:
            ``True`` if the file exists in the repository. ``False`` if it
            does not (or the parameters supplied were invalid).
        """
        try:
            self.get_file(path,
                          revision,
                          base_commit_id=base_commit_id,
                          context=context)

            return True
        except FileNotFoundError:
            return False

    def parse_diff_revision(
        self,
        filename: bytes,
        revision: bytes,
        moved: bool = False,
        copied: bool = False,
        **kwargs,
    ) -> Tuple[bytes, Union[bytes, Revision]]:
        """Return a parsed filename and revision as represented in a diff.

        A diff may use strings like ``(working copy)`` as a revision. This
        function will be responsible for converting this to something
        Review Board can understand.

        Version Changed:
            6.0:
            The first two parameters are now named ``filename`` and
            ``revision``, instead of ``file_str`` and ``revision_str``,
            for consistency with built-in tools. These names will be required
            in a future version.

        Args:
            filename (bytes):
                The filename as represented in the diff.

            revision (bytes):
                The revision as represented in the diff.

            moved (bool, optional):
                Whether the file was marked as moved in the diff.

            copied (bool, optional):
                Whether the file was marked as copied in the diff.

            **kwargs (dict):
                Additional keyword arguments. This is not currently used, but
                is available for future expansion.

        Returns:
            tuple:
            A tuple containing two items:

            Tuple:
                0 (bytes):
                    The normalized filename.

                1 (bytes or Revision):
                    The normalized revision.

        Raises:
            reviewboard.scmtools.errors.InvalidRevisionFormatError:
                The ``revision`` or ``base_commit_id`` arguments were in an
                invalid format.
        """
        raise NotImplementedError

    def get_changeset(
        self,
        changesetid: str,
        allow_empty: bool = False,
    ) -> ChangeSet:
        """Return information on a server-side changeset with the given ID.

        This only needs to be implemented if
        :py:attr:`supports_pending_changesets` is ``True``.

        Args:
            changesetid (str):
                The server-side changeset ID.

            allow_empty (bool, optional):
                Whether or not an empty changeset (one containing no modified
                files) can be returned.

                If ``True``, the changeset will be returned with whatever
                data could be provided. If ``False``, a
                :py:exc:`reviewboard.scmtools.errors.EmptyChangeSetError`
                will be raised.

                Defaults to ``False``.

        Returns:
            ChangeSet:
            The resulting changeset containing information on the commit
            and modified files.

        Raises:
            NotImplementedError:
                Changeset retrieval is not available for this type of
                repository.

            reviewboard.scmtools.errors.EmptyChangeSetError:
                The resulting changeset contained no file modifications (and
                ``allow_empty`` was ``False``).
        """
        raise NotImplementedError

    def get_repository_info(self) -> Dict[str, Any]:
        """Return information on the repository.

        The information will vary based on the repository. This data will be
        used in the API, and may be used by clients to better locate or match
        particular repositories.

        It is recommended that it contain a ``uuid`` field containing a unique
        identifier for the repository, if available.

        This is optional, and does not need to be implemented by subclasses.

        Returns:
            dict:
            A dictionary containing information on the repository.

        Raises:
            NotImplementedError:
                Repository information retrieval is not implemented by this
                type of repository. Callers should specifically check for this,
                as it's considered a valid result.
        """
        raise NotImplementedError

    def get_branches(self) -> Sequence[Branch]:
        """Return a list of all branches on the repository.

        This will fetch a list of all known branches for use in the API and
        New Review Request page.

        Subclasses that override this must be sure to always return one (and
        only one) :py:class:`Branch` result with ``default`` set to ``True``.

        Callers should check :py:attr:`supports_post_commit` before calling
        this.

        Returns:
            list of Branch:
            The list of branches in the repository. One (and only one) will
            be marked as the default branch.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                The repository tool encountered an error.

            NotImplementedError:
                Branch retrieval is not available for this type of repository.
        """
        raise NotImplementedError

    def get_commits(
        self,
        branch: Optional[str] = None,
        start: Optional[str] = None,
    ) -> Sequence[Commit]:
        """Return a list of commits backward in history from a given point.

        This will fetch a batch of commits from the repository for use in the
        API and New Review Request page.

        The resulting commits will be in order from newest to oldest, and
        should return upwards of a fixed number of commits (usually 30, but
        this depends on the type of repository and its limitations). It may
        also be limited to commits that exist on a given branch (if supported
        by the repository).

        This can be called multiple times in succession using the
        :py:attr:`Commit.parent` of the last entry as the ``start`` parameter
        in order to paginate through the history of commits in the repository.

        Callers should check :py:attr:`supports_post_commit` before calling
        this.

        Args:
            branch (str, optional):
                The branch to limit commits to. This may not be supported by
                all repositories.

            start (str, optional):
                The commit to start at. If not provided, this will fetch the
                first commit in the repository.

        Returns:
            list of Commit:
            The list of commits, in order from newest to oldest.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                The repository tool encountered an error.

            NotImplementedError:
                Commits retrieval is not available for this type of repository.
        """
        raise NotImplementedError

    def get_change(
        self,
        revision: str,
    ) -> Commit:
        """Return an individual change/commit with the given revision.

        This will fetch information on the given commit, if found, including
        its commit message and list of modified files.

        Callers should check :py:attr:`supports_post_commit` before calling
        this.

        Args:
            revision (str):
                The revision/ID of the commit.

        Returns:
            Commit:
            The resulting commit with the given revision/ID.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                Error retrieving information on this commit.

            NotImplementedError:
                Commit retrieval is not available for this type of repository.
        """
        raise NotImplementedError

    def get_parser(
        self,
        data: bytes,
    ) -> BaseDiffParser:
        """Return a diff parser used to parse diff data.

        The diff parser will be responsible for parsing the contents of the
        diff, and should expect (but validate) that the diff content is
        appropriate for the type of repository.

        Subclasses should override this.

        Args:
            data (bytes):
                The diff data to parse.

        Returns:
            reviewboard.diffviewer.diffparser.BaseDiffParser:
            The diff parser used to parse this data.
        """
        # Avoids a circular import.
        from reviewboard.diffviewer.parser import DiffParser

        return DiffParser(data)

    def normalize_path_for_display(
        self,
        filename: str,
        extra_data: Optional[JSONDict] = None,
        **kwargs,
    ) -> str:
        """Normalize a path from a diff for display to the user.

        This can take a path/filename found in a diff and normalize it,
        stripping away unwanted information, so that it displays in a better
        way in the diff viewer.

        By default, this returns the path as-is.

        Version Changed:
            3.0.19:
            Added ``extra_data`` and ``kwargs`` arguments. Subclasses that
            don't accept at least ``kwargs`` will result in a deprecation
            warning.

        Args:
            filename (str):
                The filename/path to normalize.

            extra_data (dict, optional):
                Extra data stored for the diff this file corresponds to.
                This may be empty or ``None``. Subclasses should not assume the
                presence of anything here.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            str:
            The resulting filename/path.
        """
        return filename

    def normalize_patch(
        self,
        patch: bytes,
        filename: str,
        revision: str,
    ) -> bytes:
        """Normalize a diff/patch file before it's applied.

        This can be used to take an uploaded diff file and modify it so that
        it can be properly applied. This may, for instance, uncollapse
        keywords or remove metadata that would confuse :command:`patch`.

        By default, this returns the contents as-is.

        Args:
            patch (bytes):
                The diff/patch file to normalize.

            filename (str):
                The name of the file being changed in the diff.

            revision (str):
                The revision of the file being changed in the diff.

        Returns:
            bytes:
            The resulting diff/patch file.
        """
        return patch

    @classmethod
    def popen(
        cls,
        command: List[str],
        local_site_name: Optional[str] = None,
        env: Dict[str, str] = {},
        **kwargs,
    ) -> subprocess.Popen:
        """Launch an application and return its output.

        This wraps :py:func:`subprocess.Popen` to provide some common
        parameters and to pass environment variables that may be needed by
        :command:`rbssh` (if used).

        Version Changed:
            4.0.5:
            Added ``**kwargs``.

        Args:
            command (list of str):
                The command to execute.

            local_site_name (str, optional):
                The name of the Local Site being used, if any.

            env (dict, optional):
                Extra environment variables to provide. Each key and value
                must be byte strings.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:class:`subprocess.Popen`.

                All arguments can be set or overridden except for the
                command and ``env``.

                Version Added:
                    4.0.5

        Returns:
            subprocess.Popen:
            The resulting process handle.

        Raises:
            OSError:
                Error when invoking the command. See the
                :py:func:`subprocess.Popen` documentation for more details.
        """
        new_env = {
            force_str(key): force_str(value)
            for key, value in env.items()
        }

        if local_site_name:
            new_env['RB_LOCAL_SITE'] = local_site_name

        kwargs.setdefault('stderr', subprocess.PIPE)
        kwargs.setdefault('stdout', subprocess.PIPE)
        kwargs.setdefault('close_fds', os.name != 'nt')

        return subprocess.Popen(command,
                                env=dict(os.environ, **new_env),
                                **kwargs)

    @classmethod
    def check_repository(
        cls,
        path: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        local_site_name: Optional[str] = None,
        local_site: Optional[LocalSite] = None,
        **kwargs,
    ) -> None:
        """Check a repository configuration for validity.

        This should check if a repository exists and can be connected to.
        This will also check if the repository requires an HTTPS certificate.

        The result, if the repository configuration is invalid, is returned as
        an exception. The exception may contain extra information, such as a
        human-readable description of the problem. Many types of errors can
        be returned, based on issues with the repository, authentication,
        HTTPS certificate, or SSH keys.

        If the repository configuration is valid and a connection can be
        established, this will simply return.

        Subclasses should override this to provide more specific validation
        logic.

        Args:
            path (str):
                The repository path.

            username (str, optional):
                The optional username for the repository.

            password (str, optional):
                The optional password for the repository.

            local_site_name (str, optional):
                The name of the Local Site that owns this repository. This is
                optional.

            local_site (reviewboard.site.models.LocalSite, optional):
                The :term:`Local Site` instance that owns this repository. This
                is optional.

            **kwargs (dict, unused):
                Additional settings for the repository. These will come from
                :py:attr:`auth_form` and :py:attr:`repository_form`.

        Raises:
            reviewboard.scmtools.errors.AuthenticationError:
                The provided username/password or the configured SSH key could
                not be used to authenticate with the repository.

            reviewboard.scmtools.errors.RepositoryNotFoundError:
                A repository could not be found at the given path.

            reviewboard.scmtools.errors.SCMError:
                There was a generic error with the repository or its
                configuration.  Details will be provided in the error message.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate on the server could not be verified.
                Information on the certificate will be returned in order to
                allow verification and acceptance using
                :py:meth:`accept_certificate`.

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
                An unexpected exception has occurred. Callers should check
                for this and handle it.
        """
        if sshutils.is_ssh_uri(path):
            username, hostname = SCMTool.get_auth_from_uri(path, username)
            logger.debug(
                '%s: Attempting ssh connection with host: %s, username: %s',
                cls.__name__, hostname, username)

            try:
                sshutils.check_host(hostname, username, password,
                                    local_site_name)
            except SSHAuthenticationError as e:
                # Represent an SSHAuthenticationError as a standard
                # AuthenticationError.
                raise AuthenticationError(e.allowed_types, str(e),
                                          e.user_key)
            except Exception:
                # Re-raise anything else
                raise

    @classmethod
    def get_auth_from_uri(
        cls,
        path: str,
        username: str,
    ) -> Tuple[str, str]:
        """Return the username and hostname from the given repository path.

        This is used to separate out a username and a hostname from a path,
        given a string containing ``username@hostname``.

        Subclasses do not need to provide this in most cases. It's used as
        a convenience method for :py:meth:`check_repository`. Subclasses that
        need special parsing logic will generally just replace the behavior
        in that method.

        Args:
            path (str):
                The repository path to parse.

            username (str):
                The existing username provided in the repository configuration.

        Returns:
            tuple:
            A 2-tuple containing:

            Tuple:
                0 (str):
                    The username.

                1 (str):
                    The hostname.
        """
        url = urlparse(path)

        if '@' in url[1]:
            netloc_username, hostname = url[1].split('@', 1)
        else:
            hostname = url[1]
            netloc_username = None

        if netloc_username:
            return netloc_username, hostname
        else:
            return username, hostname

    @classmethod
    def create_auth_form(
        cls,
        **kwargs,
    ) -> BaseSCMToolAuthForm:
        """Return a form for configuring repository authentication details.

        This defaults to returning an instance of :py:attr:`auth_form`
        (or :py:class:`~reviewboard.scmtools.forms.StandardSCMToolAuthForm`,
        if not explicitly set).

        Subclasses can override this to customize creation of the form.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the form's constructor.

        Returns:
            reviewboard.scmtools.forms.BaseSCMToolAuthForm:
            The repository form instance.
        """
        from reviewboard.scmtools.forms import StandardSCMToolAuthForm

        form_cls = cls.auth_form or StandardSCMToolAuthForm

        return form_cls(scmtool_cls=cls, **kwargs)

    @classmethod
    def create_repository_form(
        cls,
        **kwargs,
    ) -> BaseSCMToolRepositoryForm:
        """Return a form for configuring repository information.

        This defaults to returning an instance of :py:attr:`repository_form`
        (or :py:class:`~reviewboard.scmtools.forms.
        StandardSCMToolRepositoryForm`, if not explicitly set).

        Subclasses can override this to customize creation of the form.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the form's constructor.

        Returns:
            reviewboard.scmtools.forms.BaseSCMToolRepositoryForm:
            The repository form instance.
        """
        from reviewboard.scmtools.forms import StandardSCMToolRepositoryForm

        form_cls = cls.repository_form or StandardSCMToolRepositoryForm

        return form_cls(scmtool_cls=cls, **kwargs)

    @classmethod
    def accept_certificate(
        cls,
        path: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        local_site_name: Optional[str] = None,
        certificate: Optional[Certificate] = None,
    ) -> Mapping[str, Any]:
        """Accept the HTTPS certificate for the given repository path.

        This is needed for repositories that support HTTPS-backed
        repositories. It should mark an HTTPS certificate as accepted
        so that the user won't see validation errors in the future.

        The administration UI will call this after a user has seen and verified
        the HTTPS certificate.

        Subclasses must override this if they support HTTPS-backed
        repositories and can offer certificate verification and approval.

        Args:
            path (str):
                The repository path.

            username (str, optional):
                The username provided for the repository.

            password (str, optional):
                The password provided for the repository.

            local_site_name (str, optional):
                The name of the Local Site used for the repository, if any.

            certificate (reviewboard.scmtools.certs.Certificate):
                The certificate to accept.

        Returns:
            dict:
            Serialized information on the certificate.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                There was an error accepting the certificate.
        """
        raise NotImplementedError


class SCMClient:
    """Base class for client classes that interface with an SCM.

    Some SCMTools, rather than calling out to a third-party library, provide
    their own client class that interfaces with a command-line tool or
    HTTP-backed repository.

    While not required, this class contains functionality that may be useful to
    such client classes. In particular, it makes it easier to fetch files from
    an HTTP-backed repository, handling authentication and errors.
    """

    ######################
    # Instance variables #
    ######################

    #: The password used for communicating with the repository.
    password: Optional[str]

    #: The repository path.
    path: str

    #: The username used for communicating with the repository.
    username: Optional[str]

    def __init__(
        self,
        path: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """Initialize the client.

        Args:
            path (str):
                The repository path.

            username (str, optional):
                The username used for the repository.

            password (str, optional):
                The password used for the repository.
        """
        self.path = path
        self.username = username
        self.password = password

    def get_file_http(
        self,
        url: str,
        path: str,
        revision: RevisionID,
        mime_type: Optional[str] = None,
    ) -> Optional[bytes]:
        """Return the contents of a file from an HTTP(S) URL.

        This is a convenience for looking up the contents of files that are
        referenced in diffs through an HTTP(S) request.

        Authentication is performed using the username and password provided
        (if any).

        Args:
            url (str):
                The URL to fetch the file contents from.

            path (str):
                The path of the file, as referenced in the diff.

            revision (Revision):
                The revision of the file, as referenced in the diff.

            mime_type (str):
                The expected content type of the file. If not specified,
                this will default to accept everything.

        Returns:
            bytes:
            The contents of the file if content type matched, otherwise None.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be found.

            reviewboard.scmtools.errors.SCMError:
                Unexpected error in fetching the file. This may be an
                unexpected HTTP status code.
        """
        logger.info('Fetching file from %s', url)

        try:
            request = URLRequest(url)

            if self.username:
                credentials = '%s:%s' % (self.username, self.password)
                auth_string = \
                    force_str(base64.b64encode(credentials.encode('utf-8')))
                request.add_header(force_str('Authorization'),
                                   force_str('Basic %s' % auth_string))

            response = urlopen(request)

            if (mime_type is None or
                response.info()['Content-Type'] == mime_type):
                return force_bytes(response.read())

            return None
        except HTTPError as e:
            if e.code == 404:
                raise FileNotFoundError(path, revision)
            else:
                msg = "HTTP error code %d when fetching file from %s: %s" % \
                      (e.code, url, e)
                logger.error(msg)
                raise SCMError(msg)
        except Exception as e:
            msg = "Unexpected error fetching file from %s: %s" % (url, e)
            logger.error(msg)
            raise SCMError(msg)
