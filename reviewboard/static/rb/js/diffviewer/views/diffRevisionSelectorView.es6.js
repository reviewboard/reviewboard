/**
 * A view that allows users to select a revision of the diff to view.
 */
RB.DiffRevisionSelectorView = RB.RevisionSelectorView.extend({
    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     numDiffs (number):
     *         The total number of diff revisions available.
     */
    initialize: function(options) {
        this.options = options;

        RB.RevisionSelectorView.prototype.initialize.call(this, {
            firstLabelActive: true,
            numHandles: 2,
        });
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.DiffRevisionSelectorView:
     *     This object, for chaining.
     */
    render: function() {
        const labels = ['orig'];

        for (let i = 1; i <= this.options.numDiffs; i++) {
            labels.push(i.toString());
        }

        return RB.RevisionSelectorView.prototype.render.call(this, labels);
    },

    /**
     * Update the displayed revision based on the model.
     */
    _update: function() {
        const revision = this.model.get('revision');
        const interdiffRevision = this.model.get('interdiffRevision');

        this._values = [
            interdiffRevision ? revision : 0,
            interdiffRevision ? interdiffRevision : revision
        ];

        if (this._rendered) {
            this._updateHandles();
        }
    },

    /**
     * Callback for when one of the labels is clicked.
     *
     * This will jump to the target revision.
     *
     * TODO: we should allow people to click and drag over a range of labels to
     * select an interdiff.
     *
     * Args:
     *     ev (Event):
     *         The click event.
     */
    _onLabelClick: function(ev) {
        const $target = $(ev.currentTarget);

        this.trigger('revisionSelected', [0, $target.data('revision')]);
    },
});
