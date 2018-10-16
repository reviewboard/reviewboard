/**
 * The model for the DiffCommitListView.
 *
 * Model Attributes:
 *     commits (RB.DiffCommitCollection):
 *         The commits the view is rendering.
 *
 *     isInterdiff (boolean):
 *         Whether or not an interdiff is being rendered.
 */
RB.DiffCommitList = Backbone.Model.extend({
    defaults() {
        return {
            commits: new RB.DiffCommitCollection(),
            isInterdiff: false,
        };
    },
});
