{


const commentTypeToIDPrefix = {
    diff: '',
    file: 'f',
    screenshot: 's',
};


/**
 * Manages the review request page.
 *
 * This manages all the reviews on the page, diff fragment loading, and
 * other functionality needed for the main review request page.
 */
RB.ReviewRequestPageView = RB.ReviewablePageView.extend({
    /**
     * Initialize the page.
     */
    initialize() {
        RB.ReviewablePageView.prototype.initialize.call(this);

        this._reviewBoxListView = new RB.ReviewBoxListView({
            el: $('#reviews'),
            pageEditState: this.reviewRequestEditor,
            reviewRequestEditorView: this.reviewRequestEditorView,
            reviewRequest: this.reviewRequest,
            editorData: this.options.replyEditorData,
        });

        if (this.reviewRequestEditorView.issueSummaryTableView) {
            this.reviewRequestEditorView.issueSummaryTableView
                .on('issueClicked', this._expandIssueBox.bind(this));
        }
    },

    /**
     * Render the page.
     *
     * Returns:
     *     RB.ReviewRequestPageView:
     *     This object, for chaining.
     */
    render() {
        RB.ReviewablePageView.prototype.render.call(this);

        this._reviewBoxListView.render();

        return this;
    },

    /**
     * Queue a diff fragment for loading.
     *
     * The diff fragment will be part of a comment made on a diff.
     *
     * Args:
     *     commentID (string):
     *         The ID of the comment to load the diff fragment for.
     *
     *     key (string):
     *         Either a single filediff ID, or a pair (filediff ID and
     *         interfilediff ID) separated by a hyphen.
     */
    queueLoadDiff(commentID, key) {
        this._reviewBoxListView.diffFragmentQueue.queueLoad(commentID, key);
    },

    /**
     * Open a comment editor for the given comment.
     *
     * This is used when clicking Reply from a comment dialog on another
     * page.
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
        this._reviewBoxListView.openCommentEditor(contextType, contextID);
    },

    /**
     * Expand the review box that contains the relevent comment for the issue.
     *
     * This is used when clicking an issue from the issue summary table to
     * navigate the user to the issue comment.
     *
     * Args:
     *     commentType (string):
     *         The type of comment to expand.
     *
     *     commentID (string):
     *         The ID of the comment to expand.
     */
    _expandIssueBox(commentType, commentID) {
        const prefix = commentTypeToIDPrefix[commentType];
        const selector = `#${prefix}comment${commentID}`;

        this._reviewBoxListView._boxes.forEach(box => {
            if (box.$el.find(selector).length) {
                box.expand();
            }
        });
    },
});


}
