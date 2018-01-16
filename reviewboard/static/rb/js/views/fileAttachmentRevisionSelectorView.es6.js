/**
 * A view that allows users to select a revision of a file attachment to view.
 */
RB.FileAttachmentRevisionSelectorView = RB.RevisionSelectorView.extend({
    /**
     * Initialize the view.
     */
    initialize() {
        RB.RevisionSelectorView.prototype.initialize.call(this, {
            firstLabelActive: true,
            numHandles: 2,
        });
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.FileAttachmentRevisionSelectorView:
     *     This object, for chaining.
     */
    render() {
        const numRevisions = this.model.get('numRevisions');
        const labels = [gettext('No Diff')];

        for (let i = 1; i <= numRevisions; i++) {
            labels.push(i.toString());
        }

        RB.RevisionSelectorView.prototype.render.call(
            this, labels, true /* whether the first label is clickable */);
    },

    /**
     * Update the displayed revision based on the model.
     */
    _update() {
        const revision = this.model.get('fileRevision');
        const diffRevision = this.model.get('diffRevision');

        if (diffRevision) {
            this._values = [revision, diffRevision];
        } else {
            this._values = [0, revision];
        }

        if (this._rendered) {
            this._updateHandles();
        }
    },

    /**
     * Callback for when one of the labels is clicked.
     *
     * This will jump to the target revision.
     *
     * Args:
     *     ev (Event):
     *         The click event.
     */
    _onLabelClick(ev) {
        const $target = $(ev.currentTarget);
        this.trigger('revisionSelected', [0, $target.data('revision')]);
    },
});
