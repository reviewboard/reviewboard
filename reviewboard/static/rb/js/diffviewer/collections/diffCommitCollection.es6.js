/**
 * A collection of DiffCommits.
 */
RB.DiffCommitCollection = Backbone.Collection.extend({
    model: RB.DiffCommit,

    /**
     * Return the parent of the given commit if it exists.
     *
     * Args:
     *     commit (RB.DiffCommit):
     *         The commit to retrieve the parent of.
     *
     * Returns:
     *     RB.DiffCommit:
     *     Either the parent commit, or ``undefined`` if there is no parent in
     *     the collection.
     */
    getParent(commit) {
        return this.findWhere({
            commitID: commit.get('parentID'),
        });
    },

    /**
     * Return the first child of the commit if it exists.
     *
     * Args:
     *     commit (RB.DiffCommit):
     *         The commit to retrieve the child of.
     *
     * Returns:
     *     RB.DiffCommit:
     *     Either the child commit, or ``undefined`` if there is no child
     *     commit.
     */
    getChild(commit) {
        /*
         * Since Review Board does not support non-linear histories, we do not
         * have to worry about additional children.
         */
        return this.findWhere({
            parentID: commit.get('commitID'),
        });
    },
});
