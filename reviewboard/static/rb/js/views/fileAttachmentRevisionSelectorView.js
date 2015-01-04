/*
 * A view that allows users to select a revision of a file attachment to view.
 */
RB.FileAttachmentRevisionSelectorView = RB.RevisionSelectorView.extend({
    /*
     * Initialize the view.
     */
    initialize: function() {
        _super(this).initialize.call(this, {
            firstLabelActive: true,
            numHandles: 2
        });
    },

    /*
     * Render the view.
     */
    render: function() {
        var numRevisions = this.model.get('numRevisions'),
            labels = [gettext('No Diff')],
            i;

        for (i = 1; i <= numRevisions; i++) {
            labels.push(i.toString());
        }

        return _super(this).render.call(
            this, labels, true /* whether the first label is clickable */);
    },

    /*
     * Update the displayed revision based on the model.
     */
    _update: function() {
        var revision = this.model.get('fileRevision'),
            diffRevision = this.model.get('diffRevision');

        if (diffRevision) {
            this._values = [
                revision,
                diffRevision
            ];
        }
        else {
            this._values = [
                0,
                revision
            ];
        }

        if (this._rendered) {
            this._updateHandles();
        }
    },

    /*
     * Callback for when one of the labels is clicked.
     *
     * This will jump to the target revision.
     */
    _onLabelClick: function(ev) {
        var $target = $(ev.currentTarget);
        this.trigger('revisionSelected', [0, $target.data('revision')]);
    }
});
