"""Various utilities for working with DiffCommits."""

from __future__ import unicode_literals

import itertools
from collections import deque, namedtuple

from django.utils import six


class CommitHistoryDiffEntry(namedtuple('CommitHistoryDiffEntry',
                                        ('entry_type', 'old_commit',
                                         'new_commit'))):
    """An entry in a commit history diff."""

    COMMIT_ADDED = 'added'
    COMMIT_REMOVED = 'removed'
    COMMIT_MODIFIED = 'modified'
    COMMIT_UNMODIFIED = 'unmodified'

    entry_types = (
        COMMIT_ADDED,
        COMMIT_REMOVED,
        COMMIT_MODIFIED,
        COMMIT_UNMODIFIED
    )

    @classmethod
    def removed(cls, old_commit):
        """Create a CommitHistoryDiffEntry for a removed commit.

        Args:
            old_commit (reviewboard.diffviewer.models.DiffCommit):
                The removed commit.

        Returns:
            CommitHistoryDiffEntry:
            The history entry.
        """
        return cls(cls.COMMIT_REMOVED, old_commit, None)

    @classmethod
    def added(cls, new_commit):
        """Create a CommitHistoryDiffEntry for an added commit.

        Args:
            new_commit (reviewboard.diffviewer.models.DiffCommit):
                The added commit.

        Returns:
            CommitHistoryDiffEntry:
            The history entry.
        """
        return cls(cls.COMMIT_ADDED, None, new_commit)

    @classmethod
    def modified(cls, old_commit, new_commit):
        """Create a CommitHistoryDiffEntry for a modified commit.

        Args:
            old_commit (reviewboard.diffviewer.models.DiffCommit):
                The old commit.

            new_commit (reviewboard.diffviewer.models.DiffCommit):
                The new commit.

        Returns:
            CommitHistoryDiffEntry:
            The history entry.
        """
        return cls(cls.COMMIT_MODIFIED, old_commit, new_commit)

    @classmethod
    def unmodified(cls, old_commit, new_commit):
        """Create a CommitHistoryDiffEntry for a removed commit.

        Args:
            old_commit (reviewboard.diffviewer.models.DiffCommit):
                The old commit.

            new_commit (reviewboard.diffviewer.models.DiffCommit):
                The new commit.

        Returns:
            CommitHistoryDiffEntry:
            The history entry.
        """
        return cls(cls.COMMIT_UNMODIFIED, old_commit, new_commit)

    def __new__(cls, entry_type, old_commit, new_commit):
        """Create a a new CommitHistoryDiffEntry object.

        Args:
            entry_type (unicode):
                The commit type. This must be one of the values in
                :py:data:`entry_types`.

            old_commit (reviewboard.diffviewer.models.DiffCommit):
                The old commit. This is non-``None`` if the commit type is one
                of:

                * :py:data:`COMMIT_REMOVED`,
                * :py:data:`COMMIT_MODIFIED`, or
                * :py:data:`COMMIT_UNMODIFIED`.

            new_commit (reviewboard.diffviewer.models.DiffCommit):
                The new commit. This is non-``None`` if the commit type is one
                of:

                * :py:data:`COMMIT_ADDED`,
                * :py:data:`COMMIT_MODIFIED`, or
                * :py:data:`COMMIT_UNMODIFIED`.

        Returns:
            CommitInfo:
            The commit information object.

        Raises:
            ValueError:
                If the value of ``entry_type`` is invalid.
        """
        if entry_type not in cls.entry_types:
            raise ValueError(
                'entry_type must be one of: CommitInfo.COMMIT_ADDED,'
                'CommitInfo.COMMIT_REMOVED, CommitInfo.COMMIT_MODIFIED, or'
                'CommitInfo.COMMIT_UNMODIFIED'
            )

        if not old_commit and entry_type != cls.COMMIT_ADDED:
            raise ValueError('old_commit required for given commit type.')

        if not new_commit and entry_type != cls.COMMIT_REMOVED:
            raise ValueError('new_commit required for given commit type')

        return super(CommitHistoryDiffEntry, cls).__new__(
            cls,
            entry_type=entry_type,
            old_commit=old_commit,
            new_commit=new_commit)


def generate_commit_history_diff(old_history, new_history):
    """Generate the difference between the old and new commit histories.

    This assumes commit histories have not been re-ordered. If they have, the
    generated commit history diff may not be correct.

    Args:
        old_history (list of reviewboard.diffviewer.models.DiffCommit):
            The old commit history. This must be a linear history.

        new_history (list of reviewboard.diffviewer.models.DiffCommit):
            The new commit history. This must be a linear history.

    Yields:
        CommitHistoryDiffEntry:
        The commit history entries.
    """
    base_diffset = old_history[0].diffset

    def get_base_commits(commit):
        base_commits = []
        pending_commits = [commit]

        while pending_commits:
            commit = pending_commits.pop()
            original_commits = commit.original_commits.all()

            for base_commit in original_commits:
                if base_commit.diffset_id == base_diffset.pk:
                    base_commits.append(base_commit)
                else:
                    pending_commits.append(base_commit)

        return base_commits

    i = 0
    j = 0

    while True:
        old_commit = None
        new_commit = None
        base_commits = None

        if i < len(old_history):
            old_commit = old_history[i]

        if j < len(new_history):
            new_commit = new_history[j]
            base_commits = get_base_commits(new_commit)

        if new_commit and old_commit:
            if not base_commits:
                # This is a new commit.
                yield CommitHistoryDiffEntry.added(new_commit)
                j += 1
            elif len(base_commits) == 1:
                base_commit = base_commits[0]

                if base_commit == old_commit:
                    if new_commit.is_equivalent_to(old_commit):
                        yield CommitHistoryDiffEntry.unmodified(old_commit,
                                                                new_commit)
                    else:
                        yield CommitHistoryDiffEntry.modified(old_commit,
                                                              new_commit)
                    i += 1
                    j += 1
                else:
                    # base_commit must occur later in old_history. This means
                    # that old_commit was deleted.
                    yield CommitHistoryDiffEntry.removed(old_commit)
                    i += 1
            else:
                base_commit = base_commits[0]

                if base_commit == old_commit:
                    # We model a squash of n commits as 1 modification and
                    # n - 1 deletions.
                    yield CommitHistoryDiffEntry.modified(old_commit,
                                                          new_commit)
                    i += 1
                    j += 1

                    for commit in base_commits[1:]:
                        yield CommitHistoryDiffEntry.removed(commit)
                        i += 1
                else:
                    yield CommitHistoryDiffEntry.removed(old_commit)
                    i += 1
        elif new_commit:
            # If there are only new commits left, they must have been added.
            yield CommitHistoryDiffEntry.added(new_commit)
            j += 1
        elif old_commit:
            # If there are only old commits left, they must have been deleted.
            yield CommitHistoryDiffEntry.removed(old_commit)
            i += 1
        else:
            break


class DiffCommitFileExistenceChecker(object):
    """A file existence checker for review requests with commit history."""

    def __init__(self, repository, diffset, diff_commit):
        """Initialize the file existence checker."""
        self._repository = repository
        self._diffset = diffset
        self._diff_commit = diff_commit

    def __call__(self, path, revision, base_commit_id=None, request=None):
        """Check for the existence of the given file in the repository."""
        from reviewboard.diffviewer.models import FileDiff

        try:
            filediff = self._diffset.files.get(dest_file=path,
                                               dest_detail=revision)
            parent_commit = filediff.diff_commit
        except FileDiff.DoesNotExist:
            # If we cannot find the file in the DiffSet's FileDiffs, we fall
            # back to checking in the repository if it exists.
            return self._repository.get_file_exists(
                path,
                revision,
                base_commit_id=base_commit_id,
                request=request)

        # We must first make sure that the file exists.
        if filediff.deleted:
            return False

        # Now that we've found the file, we should make sure that the commit it
        # belongs to is an ancestor of the commit we are dealing with.

        # We pass along the current DiffCommit because if we are doing commit
        # validation, it will not be in the generated DAG because it was not
        # saved to the database. However, if it is already in the DAG, it will
        # be ignored.
        dag = self._diffset.build_commit_graph(self._diff_commit)
        commit_id = self._diff_commit.commit_id

        while commit_id in dag:
            # We only support linear histories so this is a bit of a formality.
            # once we support non-linear history, we will have to use a graph
            # search algorithm like DFS/BFS.
            assert len(dag[commit_id]) == 1

            commit_id = dag[commit_id][0]

            if commit_id == parent_commit.commit_id:
                return True

        return False


def exclude_filediff_ancestors(filediff_queryset, diffset, dag=None):
    """Return a QuerySet that excludes all ancestor FileDiffs of the DiffSet.

    If the file history graph is not given, it will be computed.
    """
    if diffset.diff_commit_count:
        if dag is None:
            dag = diffset.build_file_history_graph()

        filediff_queryset = filediff_queryset.exclude(
            pk__in=(fd.pk for fd in six.itervalues(dag)))

    return filediff_queryset


def find_ancestor_commit_ids(commit_id, commit_dag):
    """Find all ancestor commits of the commit with the given commit ID."""
    visited = set()
    unvisited = deque()
    unvisited.append(commit_id)

    # We can compute all ancestor commits by doing a depth-first traversal
    # rooted at the given commit id. All visited vertices (except for the
    # initial vertex) will be ancestors of the commit.
    while unvisited:
        vertex = unvisited.popleft()

        if vertex in visited:
            continue

        visited.add(vertex)

        for adjacent in commit_dag[vertex]:
            if adjacent in commit_dag:
                unvisited.append(adjacent)

    # A commit is not its own ancestor.
    visited.remove(commit_id)

    return visited


def find_ancestor_filediff(filediff, file_dag=None, commit_dag=None,
                           commit_id=None):
    """Return an ancestor of the given FileDiff.

    If the commit_id parameter is None, the oldest ancestor is returned.
    Otherwise, the "youngest" ancestor commit in the half-open interval
    (..., commit_id] is returned.

    An ancestor of a FileDiff is a previous revision of a FileDiff pertaining
    to the same file earlier in the commit history. Ancestor FileDiffs may or
    may not have the same name as the descendant FileDiff because the file may
    have been renamed or moved.
    """
    if file_dag is None:
        file_dag = filediff.diffset.build_file_history_graph()

    if commit_id:
        if commit_dag is None:
            commit_dag = filediff.diffset.build_commit_graph()

        # We can skip a lot of work if commit_id is not actually in the graph.
        if commit_id not in itertools.chain(six.iterkeys(commit_dag),
                                            *six.itervalues(commit_dag)):
            return None

        interval = find_ancestor_commit_ids(commit_id, commit_dag)
        interval.add(commit_id)
    else:
        interval = tuple()

    if filediff.pk not in file_dag:
        return None

    ancestor = file_dag[filediff.pk]

    if interval:
        ancestor_commit_id = ancestor.diff_commit.commit_id

    while ancestor.pk in file_dag:
        if interval:
            if ancestor_commit_id in interval:
                break

        ancestor = file_dag[ancestor.pk]

        if interval:
            ancestor_commit_id = ancestor.diff_commit.commit_id

    if interval and ancestor_commit_id not in interval:
        ancestor = None

    return ancestor
