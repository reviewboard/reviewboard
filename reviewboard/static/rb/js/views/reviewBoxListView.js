/*
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
        'click #expand-all': '_onExpandAllClicked'
    },

    /*
     * Initializes the list.
     */
    initialize: function(options) {
        this.options = options;

        this.diffFragmentQueue = new RB.DiffFragmentQueueView({
            reviewRequestPath: this.options.reviewRequest.get('reviewURL'),
            containerPrefix: 'comment_container',
            queueName: 'diff_fragments',
            el: document.getElementById('content')
        });

        this._boxes = [];
    },

    /*
     * Renders the list of review boxes.
     *
     * Each review on the page will be scanned and a ReviewBoxView will
     * be created. Along with this, a Review model will be created with
     * the information contained on the page.
     *
     * Each diff fragment that a comment references will be loaded and
     * rendered into the appropriate review boxes.
     */
    render: function() {
        var pageEditState = this.options.pageEditState,
            reviewRequest = this.options.reviewRequest;

        _.each(this.$el.children('.review'), function(reviewEl) {
            var $review = $(reviewEl),
                $body = $review.find('.body'),
                reviewID = $review.data('review-id'),
                review = reviewRequest.createReview(reviewID),
                box = new RB.ReviewBoxView({
                    el: $review,
                    model: review,
                    pageEditState: pageEditState,
                    editorData: this.options.editorData
                });

            review.set({
                shipIt: $review.data('ship-it'),
                'public': true,
                bodyTop: $body.children('.body_top').text(),
                bodyBottom: $body.children('.body_bottom').text()
            });

            box.render();

            this._boxes.push(box);
        }, this);

        _.each(this.$el.children('.changedesc'), function(changeBoxEl) {
            var box = new RB.ChangeBoxView({
                el: changeBoxEl,
                reviewRequest: reviewRequest,
                reviewRequestEditorView: this.options.reviewRequestEditorView
            });

            box.render();

            this._boxes.push(box);
        }, this);

        this.diffFragmentQueue.loadFragments();

        return this;
    },

    /*
     * Opens the comment editor for a comment with the given context type and
     * ID.
     *
     * This will look through every review and try to find the correct
     * comment editor. If found, it will open the editor.
     */
    openCommentEditor: function(contextType, contextID) {
        this._boxes.every(function(box) {
            var reviewReplyEditorView;

            if (box.getReviewReplyEditorView) {
                reviewReplyEditorView =
                    box.getReviewReplyEditorView(contextType, contextID);

                if (reviewReplyEditorView) {
                    reviewReplyEditorView.openCommentEditor();
                    return false;
                }
            }

            return true;
        });
    },

    /*
     * Handler for when the Collapse All button is pressed.
     *
     * Collapses each review box.
     */
    _onCollapseAllClicked: function() {
        _.each(this._boxes, function(box) {
            box.collapse();
        });

        return false;
    },

    /*
     * Handler for when the Expand All button is pressed.
     *
     * Expands each review box.
     */
    _onExpandAllClicked: function() {
        _.each(this._boxes, function(box) {
            box.expand();
        });

        return false;
    }
});
