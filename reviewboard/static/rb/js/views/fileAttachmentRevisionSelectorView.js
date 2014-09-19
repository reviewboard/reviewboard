/*
 * A view that allows users to select a revision of a file attachment to view.
 */
RB.FileAttachmentRevisionSelectorView = RB.RevisionSelectorView.extend({
    /*
     * Initialize the view.
     */
    initialize: function() {
        _super(this).init(1 /* number of handles */);
    },

    /*
     * Render the view.
     */
    render: function() {
        var labels = [],
            i;

        for (i = 0; i <= this.options.numRevisions; i++) {
            labels.push(i.toString());
        }

        return _super(this).render(
            labels, true /* whether the first label is clickable */);
    },

    /*
     * Update the displayed revision based on the model.
     */
    _update: function() {
        this._values = [this.model.get('revision')];

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

        this.trigger('revisionSelected', [$target.data('revision')]);
    }
});
