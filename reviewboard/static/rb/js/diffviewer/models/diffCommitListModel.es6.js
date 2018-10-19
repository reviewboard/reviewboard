/**
 * The model for the DiffCommitListView.
 *
 * Model Attributes:
 *     baseCommitID (number):
 *         The ID of the base commit, if any.
 *
 *     commits (RB.DiffCommitCollection):
 *         The commits the view is rendering.
 *
 *     historyDiff (RB.CommitHistoryDiffEntryCollection):
 *         The collection of history diff entries when displaying an interdiff.
 *
 *     tipCommitID (number):
 *         The ID of the tip commit, if any.
 */
RB.DiffCommitList = Backbone.Model.extend({
    defaults() {
        return {
            baseCommitID: null,
            commits: new RB.DiffCommitCollection(),
            historyDiff: new RB.CommitHistoryDiffEntryCollection(),
            tipCommitID: null,
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
