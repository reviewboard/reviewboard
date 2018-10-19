/**
 * The model for the DiffCommitListView.
 *
 * Model Attributes:
 *     commits (RB.DiffCommitCollection):
 *         The commits the view is rendering.
 *
 *     historyDiff (RB.CommitHistoryDiffEntryCollection):
 *         The collection of history diff entries when displaying an interdiff.
 */
RB.DiffCommitList = Backbone.Model.extend({
    defaults() {
        return {
            commits: new RB.DiffCommitCollection(),
            historyDiff: new RB.CommitHistoryDiffEntryCollection(),
        };
    },

    /**
     * Return whether or not an interdiff is being rendered.
     *
     * Returns:
     *     boolean:
     *     Whether or not an interdiff is being rendered.
     */
    isInterdiff() {
        return !this.get('historyDiff').isEmpty();
    },
});
