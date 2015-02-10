/*
 * A view that allows users to select a revision of the diff to view.
 */
RB.DiffRevisionSelectorView = RB.RevisionSelectorView.extend({
    /*
     * Initialize the view.
     */
    initialize: function() {
        RB.RevisionSelectorView.prototype.initialize.call(this, {
            firstLabelActive: true,
            numHandles: 2
        });
    },

    /*
     * Render the view.
     */
    render: function() {
        var labels = ['orig'],
            i;

        for (i = 1; i <= this.options.numDiffs; i++) {
            labels.push(i.toString());
        }

        return RB.RevisionSelectorView.prototype.render.call(this, labels);
    },

    /*
     * Update the displayed revision based on the model.
     */
    _update: function() {
        var revision = this.model.get('revision'),
            interdiffRevision = this.model.get('interdiffRevision');

        this._values = [
            interdiffRevision ? revision : 0,
            interdiffRevision ? interdiffRevision : revision
        ];

        if (this._rendered) {
            this._updateHandles();
        }
    },

    /*
     * Callback for when a single revision is selected.
     */
    _onRevisionSelected: function(ev) {
        var $target = $(ev.currentTarget);
        this.trigger('revisionSelected', [0, $target.data('revision')]);
    },

    /*
     * Callback for when an interdiff is selected.
     */
    _onInterdiffSelected: function(ev) {
        var $target = $(ev.currentTarget);
        this.trigger('revisionSelected',
                     [$target.data('first-revision'),
                      $target.data('second-revision')]);
    },

    /*
     * Callback for when one of the labels is clicked.
     *
     * This will jump to the target revision.
     *
     * TODO: we should allow people to click and drag over a range of labels to
     * select an interdiff.
     */
    _onLabelClick: function(ev) {
        var $target = $(ev.currentTarget);

        this.trigger('revisionSelected', [0, $target.data('revision')]);
    }
});
