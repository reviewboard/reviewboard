from __future__ import unicode_literals


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
        dag = self._diffset.build_dag(self._diff_commit)
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
