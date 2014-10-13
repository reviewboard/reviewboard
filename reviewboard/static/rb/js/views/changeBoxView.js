/*
 * Displays the "Review request changed" box on the review request page.
 *
 * This handles any rendering needed for special contents in the box,
 * such as the diff complexity icons and the file attachment thumbnails.
 */
RB.ChangeBoxView = RB.CollapsableBoxView.extend({
    initialize: function(options) {
        this.reviewRequest = options.reviewRequest;
        this.reviewRequestEditorView = options.reviewRequestEditorView;
    },

    render: function() {
        var $text = this.$('.changedesc-text');

        _super(this).render.call(this);

        this.reviewRequestEditorView.formatText($text);

        _.each(this.$('.diff-index tr'), function(rowEl) {
            var $row = $(rowEl),
                iconView = new RB.DiffComplexityIconView({
                    numInserts: $row.data('insert-count'),
                    numDeletes: $row.data('delete-count'),
                    numReplaces: $row.data('replace-count'),
                    totalLines: $row.data('total-line-count')
                });

            iconView.$el.appendTo($row.find('.diff-file-icon'));
            iconView.render();
        });

        _.each(this.$('.file-container'), function(thumbnailEl) {
            var $thumbnail = $(thumbnailEl),
                $caption = $thumbnail.find('.file-caption .edit'),
                model = this.reviewRequest.draft.createFileAttachment({
                    id: $thumbnail.data('file-id')
                });

            if (!$caption.hasClass('empty-caption')) {
                model.set('caption', $caption.text());
            }

            this.reviewRequestEditorView.buildFileAttachmentThumbnail(
                model, null,
                {
                    $el: $thumbnail,
                    canEdit: false
                });
        }, this);

        return this;
    }
});
