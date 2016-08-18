/**
 * Displays the "Review request changed" box on the review request page.
 *
 * This handles any rendering needed for special contents in the box,
 * such as the diff complexity icons and the file attachment thumbnails.
 */
RB.ChangeBoxView = RB.CollapsableBoxView.extend({
    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *          Options for the view.
     *
     * Option Args:
     *     reviewRequest (RB.ReviewRequest):
     *         The review request model.
     *
     *     reviewRequestEditorView (RB.ReviewRequestEditorView):
     *         The review request editor.
     */
    initialize(options) {
        this.reviewRequest = options.reviewRequest;
        this.reviewRequestEditorView = options.reviewRequestEditorView;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.ChangeBoxView:
     *     This object, for chaining.
     */
    render() {
        RB.CollapsableBoxView.prototype.render.call(this);

        this.reviewRequestEditorView.formatText(this.$('.changedesc-text'));

        _.each(this.$('.diff-index tr'), rowEl => {
            const $row = $(rowEl);
            const iconView = new RB.DiffComplexityIconView({
                numInserts: $row.data('insert-count'),
                numDeletes: $row.data('delete-count'),
                numReplaces: $row.data('replace-count'),
                totalLines: $row.data('total-line-count'),
            });

            $row.find('.diff-file-icon')
                .empty()
                .append(iconView.$el);

            iconView.render();
        });

        _.each(this.$('.file-container'), thumbnailEl => {
            const $thumbnail = $(thumbnailEl);
            const $caption = $thumbnail.find('.file-caption .edit');
            const model = this.reviewRequest.draft.createFileAttachment({
                id: $thumbnail.data('file-id')
            });

            if (!$caption.hasClass('empty-caption')) {
                model.set('caption', $caption.text());
            }

            this.reviewRequestEditorView.buildFileAttachmentThumbnail(
                model, null,
                {
                    $el: $thumbnail,
                    canEdit: false,
                });
        });

        return this;
    },
});
