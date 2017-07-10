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
    initialize(options) {
        RB.ReviewablePageView.prototype.initialize.call(this, options);

        this._boxes = [];
        this._rendered = false;

        $('#collapse-all').click(e => this._onCollapseAllClicked(e));
        $('#expand-all').click(e => this._onExpandAllClicked(e));

        this.diffFragmentQueue = new RB.DiffFragmentQueueView({
            reviewRequestPath: this.reviewRequest.get('reviewURL'),
            containerPrefix: 'comment_container',
            queueName: 'diff_fragments',
            el: document.getElementById('content'),
        });

        if (this.reviewRequestEditorView.issueSummaryTableView) {
            this.listenTo(this.reviewRequestEditorView.issueSummaryTableView,
                          'issueClicked',
                          (...args) => this._expandIssueBox(...args));
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

        /*
         * If trying to link to a review, find the box which contains that
         * review and expand it.
         */
        this._boxes.forEach(box => {
            box.render();

            // If the box contains something we're linking to, expand it.
            const selector = window.location.hash.match(/^#[A-Za-z0-9_\.-]+$/);

            if (selector && box.$(selector[0]).length > 0) {
                box.expand();
            }
        });

        this.diffFragmentQueue.loadFragments();

        this._rendered = true;

        return this;
    },

    /**
     * Add a new box to the page.
     *
     * Args:
     *     box (Backbone.View):
     *         The new box to add.
     */
    addBox(box) {
        this._boxes.push(box);

        if (this._rendered) {
            box.render();
        }
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
        this.diffFragmentQueue.queueLoad(commentID, key);
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
        for (let i = 0; i < this._boxes.length; i++) {
            const box = this._boxes[i];
            const reviewReplyEditorView = (
                _.isFunction(box.getReviewReplyEditorView)
                ? box.getReviewReplyEditorView(contextType, contextID)
                : null);

            if (reviewReplyEditorView) {
                reviewReplyEditorView.openCommentEditor();
                break;
            }
        }
    },

    /**
     * Handle a press on the Collapse All button.
     *
     * Collapses each review box.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    _onCollapseAllClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this._boxes.forEach(box => box.collapse());
    },

    /**
     * Handle a press on the Expand All button.
     *
     * Expands each review box.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    _onExpandAllClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this._boxes.forEach(box => box.expand());
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

        this._boxes.forEach(box => {
            if (box.$el.find(selector).length) {
                box.expand();
            }
        });
    },
});


}
