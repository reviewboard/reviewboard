"""Data structures and classes for defining and using SCMTools."""

from __future__ import unicode_literals

import base64
import functools
import inspect
import logging
import os
import subprocess
import warnings
from pkg_resources import iter_entry_points

from django.utils import six
from django.utils.encoding import (force_bytes, force_str, force_text,
                                   python_2_unicode_compatible)
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.parse import urlparse
from django.utils.six.moves.urllib.request import (Request as URLRequest,
                                                   urlopen)
from django.utils.translation import ugettext_lazy as _
from djblets.util.properties import TypedProperty

from reviewboard.deprecation import RemovedInReviewBoard50Warning
from reviewboard.scmtools.errors import (AuthenticationError,
                                         FileNotFoundError,
                                         SCMError)
from reviewboard.ssh import utils as sshutils
from reviewboard.ssh.errors import SSHAuthenticationError


class ChangeSet(object):
    """A server-side changeset.

    This represents information on a server-side changeset, which tracks
    the information on a commit and modified files for some types of
    repositories (such as Perforce).

    Not all data may be provided by the server.

    Attributes:
        bugs_closed (list of unicode):
            A list of bug IDs that were closed by this change.

        files (list of unicode):
            A list of filenames added/modified/deleted by the change.

        pending (bool):
            Whether or not the change is pending (not yet committed).
    """

    #: The changeset number/ID.
    changenum = TypedProperty(int)

    #: The summary of the change.
    summary = TypedProperty(six.text_type)

    #: The description of the change.
    description = TypedProperty(six.text_type)

    #: Testing information for the change.
    testing_done = TypedProperty(six.text_type)

    #: The destination branch.
    branch = TypedProperty(six.text_type)

    #: The username of the user who made the change.
    username = TypedProperty(six.text_type)

    def __init__(self):
        """Initialize the changeset."""
        self.changenum = None
        self.summary = ''
        self.description = ''
        self.testing_done = ''
        self.branch = ''
        self.bugs_closed = []
        self.files = []
        self.username = ''
        self.pending = False


@python_2_unicode_compatible
class Revision(object):
    """A revision in a diff or repository.

    This represents a specific revision in a tree, or a specialized indicator
    that can have special meaning.
    """

    #: The name/ID of the revision.
    name = TypedProperty(six.text_type, allow_none=False)

    def __init__(self, name):
        """Initialize the Revision.

        Args:
            name (unicode):
                The name of the revision. This may be a special name (which
                should be in all-uppercase) or a revision ID.

        Raises:
            TypeError:
                The provided name was not a Unicode string.
        """
        self.name = name

    def __bytes__(self):
        """Return a byte string representation of the revision.

        This is equivalent to fetching :py:attr:`name` and encoding to UTF-8.

        Returns:
            bytes:
            The name/ID of the revision.
        """
        return self.name.encode('utf-8')

    def __str__(self):
        """Return a Unicode string representation of the revision.

        This is equivalent to fetching :py:attr:`name`.

        Returns:
            unicode:
            The name/ID of the revision.
        """
        return self.name

    def __eq__(self, other):
        """Return whether this revision equals another.

        Args:
            other (Revision):
                The revision to compare to.

        Returns:
            bool:
            ``True`` if the two revisions are equal. ``False`` if they are
            not equal.
        """
        return self.name == force_text(other)

    def __ne__(self, other):
        """Return whether this revision is not equal to another.

        Args:
            other (Revision):
                The revision to compare to.

        Returns:
            bool:
            ``True`` if the two revisions are not equal. ``False`` if they are
            equal.
        """
        return self.name != force_text(other)

    def __repr__(self):
        """Return a string representation of this revision.

        Returns:
            unicode:
            The string representation.
        """
        return '<Revision: %s>' % self.name


class Branch(object):
    """A branch in a repository.

    Attributes:
        default (bool):
            Whether or not this is the default branch for the repository.

            One (and only one) branch in a list of returned branches should
            have this set to ``True``.
    """

    #: The ID of the branch.
    id = TypedProperty(six.text_type, allow_none=False)

    #: The latest commit ID on the branch.
    commit = TypedProperty(six.text_type)

    #: The name of the branch.
    name = TypedProperty(six.text_type)

    def __init__(self, id, name=None, commit='', default=False):
        """Initialize the branch.

        Args:
            id (unicode):
                The ID of the branch.

            name (unicode, optional):
                The name of the branch. If not specified, this will default
                to the ID.

            commit (unicode, optional):
                The latest commit ID on the branch.

            default (bool, optional):
                Whether or not this is the default branch for the repository.
        """
        self.id = id
        self.name = name or self.id
        self.commit = commit
        self.default = default

    def __eq__(self, other):
        """Return whether this branch is equal to another branch.

        Args:
            other (Branch):
                The branch to compare to.

        Returns:
            bool:
            ``True`` if the two branches are equal. ``False`` if they are not.
        """
        return (self.id == other.id and
                self.name == other.name and
                self.commit == other.commit and
                self.default == other.default)

    def __repr__(self):
        """Return a string representation of this branch.

        Returns:
            unicode:
            The string representation.
        """
        return ('<Branch %s (name=%s; commit=%s: default=%r)>'
                % (self.id, self.name, self.commit, self.default))


class Commit(object):
    """A commit in a repository."""

    #: The ID of the commit.
    #:
    #: This should be its SHA/revision.
    id = TypedProperty(six.text_type)

    #: The name or username of the author who made the commit.
    author_name = TypedProperty(six.text_type)

    #: The timestamp of the commit as a string in ISO 8601 format.
    date = TypedProperty(six.text_type)

    #: The commit message.
    message = TypedProperty(six.text_type)

    #: The contents of the commit's diff.
    #:
    #: This may be ``None``, depending on how the commit is fetched.
    diff = TypedProperty(bytes)

    #: The ID of the commit's parent.
    #:
    #: This should be its SHA/revision. If this is the first commit, this
    #: should be ``None`` or an empty string.
    parent = TypedProperty(six.text_type)

    def __init__(self, author_name='', id='', date='', message='', parent='',
                 diff=None):
        """Initialize the commit.

        All arguments are optional, and can be set later.

        Args:
            author_name (unicode, optional):
                The name of the author who made this commit. This should be
                the full name, if available, but can be the username or other
                identifier.

            id (unicode, optional):
                The ID of the commit. This should be its SHA/revision.

            date (unicode, optional):
                The timestamp of the commit as a string in ISO 8601 format.

            message (unicode, optional):
                The commit message.

            parent (unicode, optional):
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

    def __eq__(self, other):
        """Return whether this commit is equal to another commit.

        Args:
            other (Commit):
                The commit to compare to.

        Returns:
            bool:
            ``True`` if the two commits are equal. ``False`` if they are not.
        """
        return (self.author_name == other.author_name and
                self.id == other.id and
                self.date == other.date and
                self.message == other.message and
                self.parent == other.parent)

    def __repr__(self):
        """Return a string representation of this commit.

        Returns:
            unicode:
            The string representation.
        """
        return ('<Commit %r (author=%s; date=%s; parent=%r)>'
                % (self.id, self.author_name, self.date, self.parent))

    def split_message(self):
        """Return a split version of the commit message.

        This will separate the commit message into a summary and body, if
        possible.

        Returns:
            tuple:
            A tuple containing two string items: The summary and the commit
            message.

            If the commit message is only a single line, both items in the
            tuple will be that line.
        """
        message = self.message
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


#: Latest revision in the tree (or branch).
HEAD = Revision('HEAD')

#: Unknown revision.
#:
#: This is used to indicate that a revision could not be found or parsed.
UNKNOWN = Revision('UNKNOWN')

#: Revision representing a new file (prior to entering the repository).
PRE_CREATION = Revision('PRE-CREATION')


class _SCMToolIDProperty(object):
    """A property that automatically determines the ID for an SCMTool.

    This is used for SCMTools that don't explicitly specify a
    :py:attr:`SCMTool.scmtool_id` value. It will attempt to find a matching
    Python EntryPoint for the class and use its registration key as the ID.

    Version Added:
        3.0.16
    """

    _scmtool_ids_by_class_names = {}

    def __get__(self, owner_self, owner_cls):
        """Return the ID for the SCMTool.

        Args:
            owner_self (SCMTool, ignored):
                The instance of the tool, if requesting the value on an
                instance.

            owner_cls (type):
                The subclass of :py:class:`SCMTool`.

        Returns:
            unicode:
            The resulting SCMTool ID.

        Raises:
            ValueError:
                The ID could not be determined, as it was not registered
                by a known Python EntryPoint.
        """
        if not _SCMToolIDProperty._scmtool_ids_by_class_names:
            _SCMToolIDProperty._scmtool_ids_by_class_names = {
                '%s.%s' % (ep.module_name, ep.attrs[0]): force_text(ep.name)
                for ep in iter_entry_points('reviewboard.scmtools')
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


class SCMTool(object):
    """A backend for talking to a source code repository.

    This is responsible for handling all the communication with a repository
    and working with data provided by a repository. This includes validating
    repository configuration, fetching file contents, returning log information
    for browsing commits, constructing a diff parser for the repository's
    supported diff format(s), and more.

    Attributes:
        repository (reviewboard.scmtools.models.Repository):
            The repository owning an instance of this SCMTool.
    """

    #: A unique identifier for the SCMTool.
    #:
    #: If not provided, this will be based on its key in the
    #: ``reviewboard.scmtools`` Python EntryPoint. This will become a required
    #: attribute in a future version.
    #:
    #: Version Added:
    #:     3.0.16
    scmtool_id = _SCMToolIDProperty()

    #: The human-readable name of the SCMTool.
    #:
    #: Users will see this when they go to select a repository type. Some
    #: examples would be "Subversion" or "Perforce".
    name = None

    #: Whether or not the SCMTool supports review requests with history.
    supports_history = False

    #: Whether or not commits in this SCMTool require the committer fields.
    commits_have_committer = False

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
    supports_pending_changesets = False

    #: Whether existing commits can be browsed and posted for review.
    #:
    #: If ``True``, the New Review Request page and API will allow for
    #: browsing and posting existing commits and their diffs for review.
    supports_post_commit = False

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
    supports_raw_file_urls = False

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
    supports_ticket_auth = False

    #: Whether filenames in diffs are stored using absolute paths.
    #:
    #: This is used when uploading and validating diffs to determine if the
    #: user must supply the base path for a diff. Some types of SCMs (such as
    #: Subversion) store relative paths in diffs, requiring additional
    #: information in order to generate an absolute path for lookups.
    #:
    #: By default, this is ``False``. Subclasses must override this if their
    #: diff formats list absolute paths.
    diffs_use_absolute_paths = False

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
    prefers_mirror_path = False

    #: Overridden help text for the configuration form fields.
    #:
    #: This allows the form fields to have custom help text for the SCMTool,
    #: providing better guidance for configuration.
    field_help_text = {
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
    dependencies = {
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
    auth_form = None

    #: A custom form used to collect repository details.
    #:
    #: This allows subclasses to remove, change, or augment the standard
    #: fields for collecting a repository's path, mirror path, and other
    #: common information.
    #:
    #: Version Added:
    #:     3.0.16
    repository_form = None

    def __new__(cls, *args, **kwargs):
        """Construct a new instance of the SCMTool.

        This will perform some checks for deprecated function signatures on
        the class, fix them up and emit deprecation warnings if found, and
        then construct and initialize the instance.

        Args:
            *args (tuple):
                Positional arguments passed in during construction.

            **kwargs (dict):
                Keyword arguments passed in during construction.

        Returns:
            SCMTool:
            The new instance.
        """
        # Check for some deprecated method signatures.
        if not hasattr(cls, '__deprecations_checked'):
            for method in (cls.normalize_path_for_display,):
                argspec = inspect.getargspec(method)

                if argspec.keywords is None:
                    method_name = method.__name__

                    RemovedInReviewBoard50Warning.warn(
                        '%s.%s must accept keyword arguments. This '
                        'will be required in Review Board 5.0.'
                        % (cls.__name__, method_name))

                    @functools.wraps(method)
                    def _wrapper(_self, *_args, **_kwargs):
                        return method(_self, *_args)

                    setattr(cls, method_name, _wrapper)

            cls.__deprecations_checked = True

        # Note that we *don't* want to pass in any *args or **kwargs here.
        # Python will take care of passing them to __init__.
        return super(SCMTool, cls).__new__(cls)

    def __init__(self, repository):
        """Initialize the SCMTool.

        This will be initialized on demand, when first needed by a client
        working with a repository. It will generally be bound to the lifetime
        of the repository instance.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository owning this SCMTool.
        """
        self.repository = repository

    def get_file(self, path, revision=HEAD, base_commit_id=None, **kwargs):
        """Return the contents of a file from a repository.

        This attempts to return the raw binary contents of a file from the
        repository, given a file path and revision.

        It may also take a base commit ID, which is the ID (SHA or revision
        number) of a commit changing or introducing the file. This may differ
        from the revision for some types of repositories, where different IDs
        are used for a file content revision and a commit revision.

        Subclasses must implement this.

        Args:
            path (unicode):
                The path to the file in the repository.

            revision (Revision, optional):
                The revision to fetch. Subclasses should default this to
                :py:data:`HEAD`.

            base_commit_id (unicode, optional):
                The ID of the commit that the file was changed in. This may
                not be provided, and is dependent on the type of repository.

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

    def file_exists(self, path, revision=HEAD, base_commit_id=None, **kwargs):
        """Return whether a particular file exists in a repository.

        Like :py:meth:`get_file`, this may take a base commit ID, which is the
        ID (SHA or revision number) of a commit changing or introducing the
        file. This depends on the type of repository, and may not be provided.

        Subclasses should only override this if they have a more efficient
        way of checking for a file's existence than fetching the file contents.

        Args:
            path (unicode):
                The path to the file in the repository.

            revision (Revision, optional):
                The revision to fetch. Subclasses should default this to
                :py:data:`HEAD`.

            base_commit_id (unicode, optional):
                The ID of the commit that the file was changed in. This may
                not be provided, and is dependent on the type of repository.

            **kwargs (dict):
                Additional keyword arguments. This is not currently used, but
                is available for future expansion.

        Returns:
            bool:
            ``True`` if the file exists in the repository. ``False`` if it
            does not (or the parameters supplied were invalid).
        """
        try:
            self.get_file(path, revision, base_commit_id=base_commit_id)

            return True
        except FileNotFoundError:
            return False

    def parse_diff_revision(self, file_str, revision_str, moved=False,
                            copied=False, **kwargs):
        """Return a parsed filename and revision as represented in a diff.

        A diff may use strings like ``(working copy)`` as a revision. This
        function will be responsible for converting this to something
        Review Board can understand.

        Args:
            file_str (unicode):
                The filename as represented in the diff.

            revision_str (unicode):
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
            A tuple containing two items: The normalized filename string, and
            a :py:class:`Revision`.

        Raises:
            reviewboard.scmtools.errors.InvalidRevisionFormatError:
                The ``revision`` or ``base_commit_id`` arguments were in an
                invalid format.
        """
        raise NotImplementedError

    def get_changeset(self, changesetid, allow_empty=False):
        """Return information on a server-side changeset with the given ID.

        This only needs to be implemented if
        :py:attr:`supports_pending_changesets` is ``True``.

        Args:
            changesetid (unicode):
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

    def get_repository_info(self):
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

    def get_branches(self):
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

    def get_commits(self, branch=None, start=None):
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
            branch (unicode, optional):
                The branch to limit commits to. This may not be supported by
                all repositories.

            start (unicode, optional):
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

    def get_change(self, revision):
        """Return an individual change/commit with the given revision.

        This will fetch information on the given commit, if found, including
        its commit message and list of modified files.

        Callers should check :py:attr:`supports_post_commit` before calling
        this.

        Args:
            revision (unicode):
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

    def get_parser(self, data):
        """Return a diff parser used to parse diff data.

        The diff parser will be responsible for parsing the contents of the
        diff, and should expect (but validate) that the diff content is
        appropriate for the type of repository.

        Subclasses should override this.

        Args:
            data (bytes):
                The diff data to parse.

        Returns:
            reviewboard.diffviewer.diffparser.DiffParser:
            The diff parser used to parse this data.
        """
        # Avoids a circular import.
        from reviewboard.diffviewer.parser import DiffParser

        return DiffParser(data)

    def normalize_path_for_display(self, filename, extra_data=None, **kwargs):
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
        return filename

    def normalize_patch(self, patch, filename, revision):
        """Normalize a diff/patch file before it's applied.

        This can be used to take an uploaded diff file and modify it so that
        it can be properly applied. This may, for instance, uncollapse
        keywords or remove metadata that would confuse :command:`patch`.

        By default, this returns the contents as-is.

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
        return patch

    @classmethod
    def popen(cls, command, local_site_name=None, env={}):
        """Launch an application and return its output.

        This wraps :py:func:`subprocess.Popen` to provide some common
        parameters and to pass environment variables that may be needed by
        :command:`rbssh` (if used).

        Args:
            command (list of unicode):
                The command to execute.

            local_site_name (unicode, optional):
                The name of the Local Site being used, if any.

            env (dict, optional):
                Extra environment variables to provide. Each key and value
                must be byte strings.

        Returns:
            bytes:
            The combined output (stdout and stderr) from the command.

        Raises:
            OSError:
                Error when invoking the command. See the
                :py:func:`subprocess.Popen` documentation for more details.
        """
        new_env = {
            force_str(key): force_str(value)
            for key, value in six.iteritems(env)
        }

        if local_site_name:
            new_env[str('RB_LOCAL_SITE')] = force_bytes(local_site_name)

        return subprocess.Popen(command,
                                env=dict(os.environ, **new_env),
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                close_fds=(os.name != 'nt'))

    @classmethod
    def check_repository(cls, path, username=None, password=None,
                         local_site_name=None):
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
            path (unicode):
                The repository path.

            username (unicode, optional):
                The optional username for the repository.

            password (unicode, optional):
                The optional password for the repository.

            local_site_name (unicode, optional):
                The name of the Local Site that owns this repository. This is
                optional.

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
                An unexpected exception has ocurred. Callers should check
                for this and handle it.
        """
        if sshutils.is_ssh_uri(path):
            username, hostname = SCMTool.get_auth_from_uri(path, username)
            logging.debug(
                "%s: Attempting ssh connection with host: %s, username: %s"
                % (cls.__name__, hostname, username))

            try:
                sshutils.check_host(hostname, username, password,
                                    local_site_name)
            except SSHAuthenticationError as e:
                # Represent an SSHAuthenticationError as a standard
                # AuthenticationError.
                raise AuthenticationError(e.allowed_types, six.text_type(e),
                                          e.user_key)
            except:
                # Re-raise anything else
                raise

    @classmethod
    def get_auth_from_uri(cls, path, username):
        """Return the username and hostname from the given repository path.

        This is used to separate out a username and a hostname from a path,
        given a string containing ``username@hostname``.

        Subclasses do not need to provide this in most cases. It's used as
        a convenience method for :py:meth:`check_repository`. Subclasses that
        need special parsing logic will generally just replace the behavior
        in that method.

        Args:
            path (unicode):
                The repository path to parse.

            username (unicode):
                The existing username provided in the repository configuration.

        Returns:
            tuple:
            A tuple containing 2 string items: The username, and the hostname.
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
    def create_auth_form(cls, **kwargs):
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
    def create_repository_form(cls, **kwargs):
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
    def accept_certificate(cls, path, username=None, password=None,
                           local_site_name=None, certificate=None):
        """Accept the HTTPS certificate for the given repository path.

        This is needed for repositories that support HTTPS-backed
        repositories. It should mark an HTTPS certificate as accepted
        so that the user won't see validation errors in the future.

        The administration UI will call this after a user has seen and verified
        the HTTPS certificate.

        Subclasses must override this if they support HTTPS-backed
        repositories and can offer certificate verification and approval.

        Args:
            path (unicode):
                The repository path.

            username (unicode, optional):
                The username provided for the repository.

            password (unicode, optional):
                The password provided for the repository.

            local_site_name (unicode, optional):
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


class SCMClient(object):
    """Base class for client classes that interface with an SCM.

    Some SCMTools, rather than calling out to a third-party library, provide
    their own client class that interfaces with a command-line tool or
    HTTP-backed repository.

    While not required, this class contains functionality that may be useful to
    such client classes. In particular, it makes it easier to fetch files from
    an HTTP-backed repository, handling authentication and errors.

    Attributes:
        path (unicode):
            The repository path.

        username (unicode, optional):
            The username used for the repository.

        password (unicode, optional):
            The password used for the repository.
    """

    def __init__(self, path, username=None, password=None):
        """Initialize the client.

        Args:
            path (unicode):
                The repository path.

            username (unicode, optional):
                The username used for the repository.

            password (unicode, optional):
                The password used for the repository.
        """
        self.path = path
        self.username = username
        self.password = password

    def get_file_http(self, url, path, revision, mime_type=None):
        """Return the contents of a file from an HTTP(S) URL.

        This is a convenience for looking up the contents of files that are
        referenced in diffs through an HTTP(S) request.

        Authentication is performed using the username and password provided
        (if any).

        Args:
            url (unicode):
                The URL to fetch the file contents from.

            path (unicode):
                The path of the file, as referenced in the diff.

            revision (Revision):
                The revision of the file, as referenced in the diff.

            mime_type (unicode):
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
        logging.info('Fetching file from %s' % url)

        try:
            request = URLRequest(url)

            if self.username:
                auth_string = base64.b64encode('%s:%s' % (self.username,
                                                          self.password))
                request.add_header('Authorization', 'Basic %s' % auth_string)

            response = urlopen(request)

            if mime_type is None or response.info().gettype() == mime_type:
                return force_bytes(response.read())

            return None
        except HTTPError as e:
            if e.code == 404:
                logging.error('404')
                raise FileNotFoundError(path, revision)
            else:
                msg = "HTTP error code %d when fetching file from %s: %s" % \
                      (e.code, url, e)
                logging.error(msg)
                raise SCMError(msg)
        except Exception as e:
            msg = "Unexpected error fetching file from %s: %s" % (url, e)
            logging.error(msg)
            raise SCMError(msg)
