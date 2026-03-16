"""Utilities for dealing with DiffCommits."""

from __future__ import annotations

import base64
import json
from itertools import chain
from typing import Literal, TYPE_CHECKING

from django.utils.encoding import force_bytes
from typing_extensions import NotRequired, TypedDict

from reviewboard.scmtools.core import PRE_CREATION, UNKNOWN

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Final, TypeAlias

    from reviewboard.diffviewer.models import DiffCommit, DiffSet, FileDiff
    from reviewboard.scmtools.core import FileLookupContext
    from reviewboard.scmtools.models import Repository


class DiffCommitsValidationInfoFile(TypedDict):
    """Information on a file in a diff commit validation.

    The data contained is considered internal and should be treated by the
    caller as fully opaque.

    Version Added:
        8.0
    """

    #: The file's name.
    filename: str

    #: The file's revision.
    revision: str


class DiffCommitsValidationInfoFilesByType(TypedDict):
    """Information on files in a diff commit validation by operation type.

    This will track all added, removed, and modified files.

    The data contained is considered internal and should be treated by the
    caller as fully opaque.

    Version Added:
        8.0
    """

    #: The list of added files.
    added: list[DiffCommitsValidationInfoFile]

    #: The list of removed files.
    removed: list[DiffCommitsValidationInfoFile]

    #: The list of modified files.
    modified: list[DiffCommitsValidationInfoFile]


class DiffCommitValidationInfo(TypedDict):
    """Information on a commit in a diff commits validation tracking payload.

    This tracks all the information needed for a single commit in a commit
    series.

    The data contained is considered internal and should be treated by the
    caller as fully opaque.

    Version Added:
        8.0
    """

    #: The commit ID of the parent commit.
    parent_id: str

    #: A dictionary of the added, removed, and modified files.
    tree: DiffCommitsValidationInfoFilesByType


#: A type of entry for a commit in a commit history.
#:
#: These are all valid entry type IDs that may be included in the serialized
#: payload.
#:
#: Version Added:
#:     8.0
SerializedCommitHistoryDiffEntryType: TypeAlias = Literal[
    'added',
    'modified',
    'removed',
    'unmodified',
]


class SerializedCommitHistoryDiffEntry(TypedDict):
    """Serialized version of a CommitHistoryDiffEntry.

    Version Added:
        7.0
    """

    #: The type of change in the commit history diff.
    #:
    #: This will be one of "added", "removed", "modified", or "unmodified".
    entry_type: SerializedCommitHistoryDiffEntryType

    #: The new ID of the commit in the diff line.
    new_commit_id: NotRequired[int]

    #: The old ID of the commit in the diff line.
    old_commit_id: NotRequired[int]


#: A validation tracking payload for a series of uploaded commits.
#:
#: This is exchanged back-and-forth with API clients in order to track
#: the validation status across the upload of multiple commits.
#:
#: The data contained is considered internal and should be treated by the
#: caller as fully opaque.
#:
#: Version Added:
#:     8.0
DiffCommitsValidationInfo: TypeAlias = dict[str, DiffCommitValidationInfo]


def get_file_exists_in_history(
    validation_info: DiffCommitsValidationInfo,
    repository: Repository,
    parent_id: str,
    path: str,
    revision: str,
    base_commit_id: (str | None) = None,
    *,
    context: (FileLookupContext | None) = None,
    **kwargs,
) -> bool:
    """Return whether or not the file exists, given the validation information.

    This will walk through the commit chain in ``validation_info``, starting
    with ``parent_id``, looking for a file entry that matches the given
    ``path`` and (by default) ``revision``. If found, the file is considered
    to exist. If not found, it will fall back to checking the repository.

    This can also operate in a loose validation mode. In this mode, only
    file paths are compared, not revisions. This is required for diffs that
    don't provide per-file revision information (such as Mercurial's plain
    and Git-style diffs). If a match is found, the associated commit ID is
    stored as ``context.file_extra_data['__validated_parent_id']``, allowing
    for post-processing of the source revision to occur.

    Strict validation mode is the default. Loose validation must be opted into
    by setting ``context.diff_extra_data['has_per_file_revisions'] = False``.
    This is done automatically when a
    :py:class:`~reviewboard.diffviewer.parser.BaseDiffParser` subclass sets
    :py:attr:`has_per_file_revisions
    <reviewboard.diffviewer.parser.BaseDiffParser.has_per_file_revisions>`
    to ``False``.

    Version Changed:
        7.0.2:
        * Added the ``context`` argument.
        * Added the loose validation mode.

    Version Changed:
        4.0.5:
        Removed explicit arguments for ``base_commit_id`` and ``request``, and
        added ``**kwargs``.

    Args:
        validation_info (dict):
            Validation metadata generated by the
            :py:class:`~reviewboard.webapi.resources.validate_diffcommit.
            ValidateDiffCommitResource`.

        repository (reviewboard.scmtools.models.Repository):
            The repository.

        parent_id (str):
            The parent commit ID of the commit currently being processed.

        path (str):
            The file path.

        revision (str):
            The revision of the file to retrieve.

        base_commit_id (str, optional):
            The commit ID to use for the base of the changes.

        context (reviewboard.scmtools.core.FileLookupContext, optional):
            The file lookup context used to validate this repository.

            Version Added:
                7.0.2

        **kwargs (dict):
            Additional keyword arguments normally expected by
            :py:meth:`Repository.get_file_exists
            <reviewboard.scmtools.models.Repository.get_file_exists>`.

            Version Added:
                4.0.5

    Returns:
        bool:
        Whether or not the file exists.
    """
    match_parent_revisions = (
        context is None or
        context.diff_extra_data.get('has_per_file_revisions', True))

    while parent_id in validation_info:
        entry = validation_info[parent_id]
        tree = entry['tree']

        if revision == UNKNOWN:
            for removed_info in tree['removed']:
                if removed_info['filename'] == path:
                    return False

        for change_info in chain(tree['added'], tree['modified']):
            if change_info['filename'] == path:
                if revision == UNKNOWN:
                    return True

                if match_parent_revisions:
                    # In the standard case, we have per-file revisions, and
                    # can use that to get a specific match within the
                    # validation history.
                    if change_info['revision'] == revision:
                        return True
                else:
                    # In a more limited case, we may not know the per-file
                    # revision, and instead have to limit our scan to
                    # the nearest filename. This is the case with Mercurial
                    # diffs.
                    #
                    # We'll be recording what we found, temporarily. This
                    # will be used to update the source filename of a
                    # generated FileDiff.
                    assert context is not None

                    context.file_extra_data['__validated_parent_id'] = \
                        parent_id

                    return True

        parent_id = entry['parent_id']

    # We did not find an entry in our validation info, so we need to fall back
    # to checking the repository.
    return repository.get_file_exists(path=path,
                                      revision=revision,
                                      base_commit_id=base_commit_id,
                                      context=context,
                                      **kwargs)


def exclude_ancestor_filediffs(
    to_filter: Sequence[FileDiff],
    all_filediffs: (Sequence[FileDiff] | None) = None,
) -> Sequence[FileDiff]:
    """Exclude all ancestor FileDiffs from the given list and return the rest.

    A :pyclass:`~reviewboard.diffviewer.models.filediff.FileDiff` is considered
    an ancestor of another if it occurs in a previous commit and modifies the
    same file.

    As a result, only the most recent (commit-wise) FileDiffs that modify a
    given file will be included in the result.

    Args:
        to_filter (list of reviewboard.diffviewer.models.filediff.FileDiff):
            The FileDiffs to filter.

        all_filediffs (list of reviewboard.diffviewer.models.filediff.FileDiff,
                       optional):
            The list of all FileDiffs in the :py:class:`~reviewboard.
            diffviewer.models.diffset.DiffSet>`.

            If not provided, it is assumed that ``to_filter`` is a list of all
            FileDiffs in the :py:class:`~reviewboard.diffviewer.models.
            diffset.DiffSet>`.

    Returns:
        list of reviewboard.diffviewer.models.filediff.FileDiff:
        The FileDiffs that are not ancestors of other FileDiffs.
    """
    if all_filediffs is None:
        all_filediffs = to_filter

    ancestor_pks = {
        ancestor.pk
        for filediff in to_filter
        for ancestor in filediff.get_ancestors(minimal=False,
                                               filediffs=all_filediffs)
    }

    return [
        filediff
        for filediff in to_filter
        if filediff.pk not in ancestor_pks
    ]


def deserialize_validation_info(
    raw: str | bytes,
) -> DiffCommitsValidationInfo:
    """Deserialize the raw validation info.

    Args:
        raw (str or bytes):
            The raw validation info from the client.

    Returns:
        DiffCommitsValidationInfo:
        The deserialized validation info.

    Raises:
        ValueError:
            Either the data could not be base64-decoded or the resulting JSON
            was of an invalid format (i.e., it was not a dictionary).

        TypeError:
            The base64-decoded data could not be interpreted as JSON.
    """
    value = json.loads(base64.b64decode(force_bytes(raw)).decode('utf-8'))

    if not isinstance(value, dict):
        raise ValueError('Invalid format.')

    return value


def serialize_validation_info(
    info: DiffCommitsValidationInfo,
) -> str:
    """Serialize the given validation info into a raw format.

    Args:
        info (DiffCommitsValidationInfo):
            The dictionary of validation info.

    Returns:
        str:
        The base64-encoded JSON of the validation info.
    """
    data = json.dumps(info).encode('utf-8')

    return base64.b64encode(data).decode('utf-8')


def update_validation_info(
    validation_info: DiffCommitsValidationInfo,
    commit_id: str,
    parent_id: str,
    filediffs: Sequence[FileDiff],
) -> DiffCommitsValidationInfo:
    """Update the validation info with a new commit.

    Args:
        validation_info (DiffCommitsValidationInfo):
            The dictionary of validation info. This will be modified in-place.

            This is a mapping of commit IDs to their metadata. Each metadata
            dictionary contains the following keys:

            ``parent_id``:
                The commit ID of the parent commit.

            ``tree``:
                A dictionary of the added, removed, and modified files in this
                commit.

        commit_id (str):
            The commit ID of the commit whose metadata is being added to the
            dictionary.

            This must not already be present in ``validation_info``.

        parent_id (str):
            The commit ID of the parent commit.

            This must be present in ``validation_info`` *unless* this is the
            first commit being added (i.e., ``validation_info`` is empty).

        filediffs (list of reviewboard.diffviewer.models.filediff.FileDiff):
            The parsed FileDiffs from :py:func:`~reviewboard.diffviewer.
            filediff_creator.create_filediffs`.

    Returns:
        DiffCommitsValidationInfo:
        The dictionary of validation info.
    """
    from reviewboard.diffviewer.models import FileDiff

    assert validation_info == {} or parent_id in validation_info
    assert commit_id not in validation_info

    added: list[DiffCommitsValidationInfoFile] = []
    removed: list[DiffCommitsValidationInfoFile] = []
    modified: list[DiffCommitsValidationInfoFile] = []

    for f in filediffs:
        if f.status in {FileDiff.DELETED, FileDiff.MOVED}:
            removed.append({
                'filename': f.source_file,
                'revision': f.source_revision,
            })

        if (f.status in {FileDiff.COPIED, FileDiff.MOVED} or
            (f.status == FileDiff.MODIFIED and
             f.source_revision == PRE_CREATION)):
            added.append({
                'filename': f.dest_file,
                'revision': f.dest_detail,
            })
        elif f.status == FileDiff.MODIFIED:
            modified.append({
                'filename': f.dest_file,
                'revision': f.dest_detail,
            })

    validation_info[commit_id] = {
        'parent_id': parent_id,
        'tree': {
            'added': added,
            'modified': modified,
            'removed': removed,
        },
    }

    return validation_info


class CommitHistoryDiffEntry:
    """An entry in a commit history diff."""

    COMMIT_ADDED: Final[SerializedCommitHistoryDiffEntryType] = 'added'
    COMMIT_REMOVED: Final[SerializedCommitHistoryDiffEntryType] = 'removed'
    COMMIT_MODIFIED: Final[SerializedCommitHistoryDiffEntryType] = 'modified'
    COMMIT_UNMODIFIED: Final[SerializedCommitHistoryDiffEntryType] = \
        'unmodified'

    #: The valid entry types.
    #:
    #: Version Changed:
    #:     8.0:
    #:     Renamed from ``entry_types`` and changed the type to a set.
    ENTRY_TYPES: set[SerializedCommitHistoryDiffEntryType] = {
        COMMIT_ADDED,
        COMMIT_REMOVED,
        COMMIT_MODIFIED,
        COMMIT_UNMODIFIED,
    }

    ######################
    # Instance variables #
    ######################

    #: The commit type.
    entry_type: SerializedCommitHistoryDiffEntryType

    #: The new commit.
    new_commit: DiffCommit | None

    #: The old commit.
    old_commit: DiffCommit | None

    def __init__(
        self,
        entry_type: SerializedCommitHistoryDiffEntryType,
        old_commit: (DiffCommit | None) = None,
        new_commit: (DiffCommit | None) = None,
    ) -> None:
        """Initialize the CommitHistoryDiffEntry object.

        Args:
            entry_type (str):
                The commit type. This must be one of the values in
                :py:attr:`entry_types`.

            old_commit (reviewboard.diffviewer.models.diffcommit.DiffCommit,
                        optional):
                The old commit. This is required if the commit type is one of:

                * :py:data:`COMMIT_REMOVED`
                * :py:data:`COMMIT_MODIFIED`
                * :py:data:`COMMIT_UNMODIFIED`

            new_commit (reviewboard.diffviewer.models.diffcommit.DiffCommit,
                        optional):
                The new commit. This is required if the commit type is one of:

                * :py:data:`COMMIT_ADDED`
                * :py:data:`COMMIT_MODIFIED`
                * :py:data:`COMMIT_UNMODIFIED`

        Raises:
            ValueError:
                The value of ``entry_type`` was invalid or the wrong commits
                were specified.
        """
        if entry_type not in self.ENTRY_TYPES:
            raise ValueError(f'Invalid entry_type: "{entry_type}"')

        if not old_commit and entry_type != self.COMMIT_ADDED:
            raise ValueError('old_commit required for given commit type.')

        if not new_commit and entry_type != self.COMMIT_REMOVED:
            raise ValueError('new_commit required for given commit type')

        self.entry_type = entry_type
        self.old_commit = old_commit
        self.new_commit = new_commit

    def serialize(self) -> SerializedCommitHistoryDiffEntry:
        """Serialize the entry to a dictionary.

        Returns:
            SerializedCommitHistoryDiffEntry:
            A dictionary of the serialized information.
        """
        result: SerializedCommitHistoryDiffEntry = {
            'entry_type': self.entry_type,
        }

        if self.new_commit:
            result['new_commit_id'] = self.new_commit.pk

        if self.old_commit:
            result['old_commit_id'] = self.old_commit.pk

        return result

    def __eq__(
        self,
        other: object,
    ) -> bool:
        """Compare two entries for equality.

        Two entries are equal if and only if their attributes match.

        Args:
            other (object):
                The object to compare against.

        Returns:
            bool:
            Whether or not this entry and the other entry are equal.
        """
        return (type(other) is CommitHistoryDiffEntry and
                self.entry_type == other.entry_type and
                self.old_commit == other.old_commit and
                self.new_commit == other.new_commit)

    def __ne__(
        self,
        other: object,
    ) -> bool:
        """Compare two entries for inequality.

        Two entries are not equal if and only if any of their attributes don't
        match.

        Args:
            other (object):
                The object to compare against.

        Returns:
            bool:
            Whether or not this entry and the other entry are not equal.
        """
        return not self == other

    def __repr__(self) -> str:
        """Return a string representation of the entry.

        Returns:
            str:
            A string representation of the entry.
        """
        return (
            f'<CommitHistoryDiffEntry(entry_type={self.entry_type}, '
            f'old_commit={self.old_commit}, new_commit={self.new_commit})>'
        )


def diff_histories(
    old_history: Sequence[DiffCommit],
    new_history: Sequence[DiffCommit],
) -> Iterator[CommitHistoryDiffEntry]:
    """Yield the entries in the diff between the old and new histories.

    Args:
        old_history (list of reviewboard.diffviewer.models.DiffCommit):
            The list of commits from a previous
            :py:class:`~reviewboard.diffviewer.models.diffset.DiffSet`.

        new_history (list of reviewboard.diffviewer.models.DiffCommit):
            The list of commits from the new
            :py:class:`~reviewboard.diffviewer.models.diffset.DiffSet`.

    Yields:
        CommitHistoryDiffEntry:
        The history entries.
    """
    i = 0

    # This is not quite the same as ``enumerate(...)`` because if we run out
    # of history, ``i`` will not be incremented.

    for old_commit, new_commit in zip(old_history, new_history):
        if old_commit.commit_id != new_commit.commit_id:
            break

        yield CommitHistoryDiffEntry(
            entry_type=CommitHistoryDiffEntry.COMMIT_UNMODIFIED,
            old_commit=old_commit,
            new_commit=new_commit)

        i += 1

    for old_commit in old_history[i:]:
        yield CommitHistoryDiffEntry(
            entry_type=CommitHistoryDiffEntry.COMMIT_REMOVED,
            old_commit=old_commit)

    for new_commit in new_history[i:]:
        yield CommitHistoryDiffEntry(
            entry_type=CommitHistoryDiffEntry.COMMIT_ADDED,
            new_commit=new_commit)


def get_base_and_tip_commits(
    base_commit_id: int | None,
    tip_commit_id: int | None,
    diffset: (DiffSet | None) = None,
    commits: (Sequence[DiffCommit] | None) = None,
) -> tuple[DiffCommit | None, DiffCommit | None]:
    """Return the base and tip commits specified.

    Args:
        base_commit_id (int):
            The primary key of the requested base commit. This may be ``None``,
            in which case a base commit will not be looked up or returned.

        tip_commit_id (int):
            The primary key of the requested tip commit. This may be ``None``,
            in which case a tip commit will not be looked up or returned.

        diffset (reviewboard.diffviewer.models.diffset.DiffSet, optional):
            The diffset that the commits belong to.

            This argument is only required if ``commits`` is ``None``.

        commits (list of reviewboard.diffviewer.models.diffcommit.DiffCommit,
                 optional):
            A pre-fetched list of commits to use instead of querying the
            database.

            If this argument is not provided, ``diffset`` must be provided to
            limit the database query to that DiffSet's commits.

    Returns:
        tuple:
        A 2-tuple of the following:

        Tuple:
            0 (reviewboard.diffviewer.models.diffcommit.DiffCommit):
                The requested based commit.

            1 (reviewboard.diffviewer.models.diffcommit.DiffCommit):
                The requested tip commit.

        If either the base or tip commit are not requested or they cannot be
        found, then their corresponding entry in the tuple will be ``None``.
    """
    if commits is None:
        if diffset is None:
            raise ValueError(
                'get_base_and_tip_commits() requires either diffset or '
                'commits to be provided.')

        commit_ids: list[int] = []

        if base_commit_id is not None:
            commit_ids.append(base_commit_id)

        if tip_commit_id is not None:
            commit_ids.append(tip_commit_id)

        if commit_ids:
            commits = list(diffset.commits.filter(pk__in=commit_ids))

    if not commits:
        return None, None

    base_commit: (DiffCommit | None) = None
    tip_commit: (DiffCommit | None) = None

    if base_commit_id is not None or tip_commit_id is not None:
        for commit in commits:
            if base_commit_id == commit.pk:
                base_commit = commit

            if tip_commit_id == commit.pk:
                tip_commit = commit

    return base_commit, tip_commit
