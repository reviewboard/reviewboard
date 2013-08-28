/*
 * Manages the review request page.
 *
 * This manages all the reviews on the page, diff fragment loading, and
 * other functionality needed for the main review request page.
 */
RB.ReviewRequestPageView = RB.ReviewablePageView.extend({
    /*
     * Initializes the page.
     */
    initialize: function() {
        RB.ReviewablePageView.prototype.initialize.call(this);

        this._reviewBoxListView = new RB.ReviewBoxListView({
            el: $('#content'),
            pageEditState: this.reviewRequestEditor,
            reviewRequest: this.reviewRequest
        });
    },

    /*
     * Renders the page.
     */
    render: function() {
        RB.ReviewablePageView.prototype.render.call(this);

        this._reviewBoxListView.render();

        return this;
    },

    /*
     * Queues a diff fragment for loading.
     *
     * The diff fragment will be part of a comment made on a diff.
     */
    queueLoadDiff: function(commentID, key) {
        this._reviewBoxListView.diffFragmentQueue.queueLoad(commentID, key);
    },

    /*
     * Opens a comment editor for the given comment.
     *
     * This is used when clicking Reply from a comment dialog on another
     * page.
     */
    openCommentEditor: function(contextType, contextID) {
        this._reviewBoxListView.openCommentEditor(contextType, contextID);
    }
});
