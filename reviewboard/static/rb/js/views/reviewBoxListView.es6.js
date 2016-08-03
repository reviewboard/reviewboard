/**
 * Manages a page full of review boxes.
 *
 * Each review box this creates represents one public review.
 * A ReviewBoxView will be set up for each one.
 *
 * This will also begin loading each section of a diff that contains comments,
 * and rendering them in the appropriate boxes.
 */
RB.ReviewBoxListView = Backbone.View.extend({
    events: {
        'click #collapse-all': '_onCollapseAllClicked',
        'click #expand-all': '_onExpandAllClicked',
    },

    /**
     * Initialize the list.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     reviewRequest (RB.ReviewRequest):
     *         The review request model.
     *
     *     reviewRequestEditorView (RB.ReviewRequestEditorView):
     *         The editor view.
     *
     *     reviewRequestEditor (RB.ReviewRequestEditor):
     *         The editor model.
     *
     *     showSendEmail (boolean):
     *         Whether to show the "Send E-mail" box on replies.
     */
    initialize(options) {
        this.options = options;

        this.diffFragmentQueue = new RB.DiffFragmentQueueView({
            reviewRequestPath: this.options.reviewRequest.get('reviewURL'),
            containerPrefix: 'comment_container',
            queueName: 'diff_fragments',
            el: document.getElementById('content'),
        });

        this._boxes = [];
    },

    /**
     * Render the list of review boxes.
     *
     * Each review on the page will be scanned and a ReviewBoxView will
     * be created. Along with this, a Review model will be created with
     * the information contained on the page.
     *
     * Each diff fragment that a comment references will be loaded and
     * rendered into the appropriate review boxes.
     *
     * Returns:
     *     RB.ReviewBoxListView:
     *     This object, for chaining.
     */
    render() {
        _.each(this.$el.children('.review'), reviewEl => {
            const $review = $(reviewEl);
            const $body = $review.find('.body');
            const reviewID = $review.data('review-id');

            const review = this.options.reviewRequest.createReview(reviewID);
            review.set({
                shipIt: $review.data('ship-it'),
                'public': true,
                bodyTop: $body.children('.body_top').text(),
                bodyBottom: $body.children('.body_bottom').text(),
            });

            const box = new RB.ReviewBoxView({
                el: $review,
                model: review,
                reviewRequestEditor: this.options.reviewRequestEditor,
                showSendEmail: this.options.showSendEmail,
            });
            box.render();

            this._boxes.push(box);
        });

        _.each(this.$el.children('.changedesc'), changeBoxEl => {
            const box = new RB.ChangeBoxView({
                el: changeBoxEl,
                reviewRequest: this.options.reviewRequest,
                reviewRequestEditorView: this.options.reviewRequestEditorView,
            });

            box.render();

            this._boxes.push(box);
        });

        this.diffFragmentQueue.loadFragments();

        return this;
    },

    /**
     * Opens the comment editor for a comment.
     *
     * This will look through every review and try to find the correct
     * comment editor. If found, it will open the editor.
     *
     * Args:
     *     contextType (string):
     *         The type of object being edited (such as ``body_top`` or
     *         ``diff_comments``)
     *
     *     contextID (number, optional):
     *         The ID of the comment being edited, if appropriate.
     */
    openCommentEditor(contextType, contextID) {
        for (let i = 0; i < this._boxes.length; i++) {
            const box = this._boxes[i];

            if (box.getReviewReplyEditorView) {
                const reviewReplyEditorView =
                    box.getReviewReplyEditorView(contextType, contextID);

                if (reviewReplyEditorView) {
                    reviewReplyEditorView.openCommentEditor();
                    break;
                }
            }
        }
    },

    /**
     * Handle a press on the Collapse All button.
     *
     * Collapses each review box.
     *
     * Returns:
     *     boolean:
     *     false, always.
     */
    _onCollapseAllClicked() {
        this._boxes.forEach(box => box.collapse());
        return false;
    },

    /**
     * Handle a press on the Expand All button.
     *
     * Expands each review box.
     *
     * Returns:
     *     boolean:
     *     false, always.
     */
    _onExpandAllClicked() {
        this._boxes.forEach(box => box.expand());
        return false;
    },
});
