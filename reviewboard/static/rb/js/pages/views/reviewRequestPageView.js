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
            reviewRequestEditorView: this.reviewRequestEditorView,
            reviewRequest: this.reviewRequest
        });

        if (this.reviewRequestEditorView.issueSummaryTableView) {
            this.reviewRequestEditorView.issueSummaryTableView
                .on('issueClicked', _.bind(this._expandIssueBox, this));
        }
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
    },

    /*
     * Expands the review box that contains the relevent comment for the issue.
     *
     * This is used when clicking an issue from the issue summary table to
     * navigate the user to the issue comment.
     */
    _expandIssueBox: function(commentAttributes) {
        var typeToPrefixMap = {
                diff: '',
                file: 'f',
                screenshot: 's'
            },
            selector = '#' + typeToPrefixMap[commentAttributes.type] +
                       'comment' + commentAttributes.id;

        _.each(this._reviewBoxListView._boxes, function(box) {
            if (box.$el.find(selector).length) {
                box.expand();
            }
        });
    }
});
