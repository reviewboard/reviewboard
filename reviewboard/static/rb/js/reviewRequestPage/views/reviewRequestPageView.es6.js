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
RB.ReviewRequestPage.ReviewRequestPageView = RB.ReviewablePageView.extend({
    events: {
        'click #collapse-all': '_onCollapseAllClicked',
        'click #expand-all': '_onExpandAllClicked',
    },

    /**
     * Initialize the page.
     */
    initialize(options) {
        RB.ReviewablePageView.prototype.initialize.call(this, options);

        this._entryViews = [];
        this._rendered = false;
        this._issueSummaryTableView = null;

        this.diffFragmentQueue = new RB.DiffFragmentQueueView({
            reviewRequestPath: this.reviewRequest.get('reviewURL'),
            containerPrefix: 'comment_container',
            queueName: 'diff_fragments',
            el: document.getElementById('content'),
        });
    },

    /**
     * Render the page.
     *
     * Returns:
     *     RB.ReviewRequestPage.ReviewRequestPageView:
     *     This object, for chaining.
     */
    render() {
        RB.ReviewablePageView.prototype.render.call(this);

        /*
         * Render each of the entries on the page.
         *
         * If trying to link to some anchor in some entry, we'll expand the
         * first entry containing that anchor.
         */
        const selector = window.location.hash.match(/^#[A-Za-z0-9_\.-]+$/);
        let anchorFound = false;

        this._entryViews.forEach(entryView => {
            entryView.render();

            if (!anchorFound &&
                selector &&
                entryView.$(selector[0]).length > 0) {
                /*
                 * We found the entry containing the specified anchor. Expand
                 * it and stop searching the rest of the entries.
                 */
                entryView.expand();
                anchorFound = true;
            }
        });

        this.diffFragmentQueue.loadFragments();

        this._issueSummaryTableView =
            new RB.ReviewRequestPage.IssueSummaryTableView({
                el: $('#issue-summary'),
                model: this.reviewRequestEditor.get('commentIssueManager'),
            });
        this._issueSummaryTableView.render();

        this.listenTo(this._issueSummaryTableView,
                      'issueClicked',
                      this._onIssueClicked);

        this._rendered = true;

        return this;
    },

    /**
     * Add a new entry and view to the page.
     *
     * Args:
     *     entryView (RB.ReviewRequestPage.EntryView):
     *         The new entry's view to add.
     */
    addEntryView(entryView) {
        this._entryViews.push(entryView);

        if (this._rendered) {
            entryView.render();
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
        for (let i = 0; i < this._entryViews.length; i++) {
            const entryView = this._entryViews[i];
            const reviewReplyEditorView = (
                _.isFunction(entryView.getReviewReplyEditorView)
                ? entryView.getReviewReplyEditorView(contextType, contextID)
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
     * Collapses each entry.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    _onCollapseAllClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this._entryViews.forEach(entryView => entryView.collapse());
    },

    /**
     * Handle a press on the Expand All button.
     *
     * Expands each entry.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    _onExpandAllClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this._entryViews.forEach(entryView => entryView.expand());
    },

    /**
     * Handler for when an issue in the issue summary table is clicked.
     *
     * This will expand the review entry that contains the comment for the
     * issue, and navigate to the comment.
     *
     * Args:
     *     params (object):
     *         Parameters passed to the event handler.
     */
    _onIssueClicked(params) {
        const prefix = commentTypeToIDPrefix[params.commentType];
        const selector = `#${prefix}comment${params.commentID}`;

        this._entryViews.forEach(entryView => {
            if (entryView.$el.find(selector).length > 0) {
                entryView.expand();
            }
        });

        window.location = params.commentURL;
    },
});


}
