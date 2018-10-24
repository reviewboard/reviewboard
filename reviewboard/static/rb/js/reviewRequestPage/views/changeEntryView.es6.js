(function() {


const ParentView = RB.ReviewRequestPage.BaseStatusUpdatesEntryView;


/**
 * Displays the "Review request changed" entry on the review request page.
 *
 * This handles any rendering needed for special contents in the box,
 * such as the diff complexity icons and the file attachment thumbnails.
 */
RB.ReviewRequestPage.ChangeEntryView = ParentView.extend({
    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *          Options for the view.
     *
     * Option Args:
     *     reviewRequestEditorView (RB.ReviewRequestEditorView):
     *         The review request editor.
     */
    initialize(options) {
        ParentView.prototype.initialize.apply(this, arguments);

        const reviewRequestEditor = this.model.get('reviewRequestEditor');

        this.reviewRequest = reviewRequestEditor.get('reviewRequest');
        this.reviewRequestEditorView = options.reviewRequestEditorView;

        this._commitListView = null;

        this._$boxStatus = null;
        this._$fixItLabel = null;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.ReviewRequestPage.ChangeEntryView:
     *     This object, for chaining.
     */
    render() {
        ParentView.prototype.render.call(this);

        this._$boxStatus = this.$('.box-status');
        this._$fixItLabel = $('<label class="fix-it-label">')
            .hide()
            .appendTo(this.$('.labels-container'));

        RB.formatText(this.$('.changedesc-text'), {
            bugTrackerURL: this.reviewRequest.get('bugTrackerURL'),
            isHTMLEncoded: true,
        });

        this._updateLabels();

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

        const commits = this.model.get('commits');

        if (commits) {
            this._commitListView = new RB.DiffCommitListView({
                el: this.$('.commit-list-container'),
                model: new RB.DiffCommitList({
                    commits: commits,
                    diffHistory: new RB.CommitHistoryDiffEntryCollection(),
                }),
            });
        }

        return this;
    },

    /**
     * Set up a review view.
     *
     * This will begin listening for changes to the issue counts and
     * update the labels on the box.
     *
     * Args:
     *     view (RB.ReviewRequestPage.ReviewView):
     *         The review view being set up.
     */
    setupReviewView(view) {
        this.listenTo(view, 'openIssuesChanged', this._updateLabels);
    },

    /**
     * Update the "Fix It" label based on the open issue counts.
     *
     * If there are open issues, there will be a "Fix it!" label.
     */
    _updateLabels() {
        if (this._reviewViews.some(view => view.hasOpenIssues())) {
            const openIssueCount = this._reviewViews.reduce(
                (sum, view) => sum + view.getOpenIssueCount(),
                0);

            this._$boxStatus.addClass('has-issues');
            this._$fixItLabel
                .empty()
                .append(
                    $('<span class="open-issue-count">')
                        .text(interpolate(gettext('%s failed'),
                                          [openIssueCount]))
                )
                .append(document.createTextNode(gettext('Fix it!')))
                .show()
                .css({
                    opacity: 1,
                    left: 0,
                });
        } else {
            this._$fixItLabel.css({
                opacity: 0,
                left: '-100px',
            });
            this._$boxStatus.removeClass('has-issues');
        }
    }
});


})();
