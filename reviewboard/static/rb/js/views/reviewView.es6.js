/**
 * Handles interaction for a review on the review request page. These can be
 * contained within the main review entries, but also for status updates in
 * change description entries or the initial status updates entry.
 */
RB.ReviewView = Backbone.View.extend({
    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     reviewRequestEditor (RB.ReviewRequestEditor):
     *         The review request editor.
     */
    initialize(options) {
        this.options = options;

        this._bannerView = null;
        this._draftBannerShown = false;
        this._openIssueCount = 0;
        this._reviewReply = null;
        this._replyEditors = [];
        this._replyEditorViews = [];

        this._setupNewReply();
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.ReviewView:
     *     This object, for chaining.
     */
    render() {
        _.each(this.$('.review-comments .issue-indicator'), el => {
            const $issueState = $('.issue-state', el);

            /*
             * Not all issue-indicator divs have an issue-state div for the
             * issue bar.
             */
            if ($issueState.length > 0) {
                const issueStatus = $issueState.data('issue-status');

                if (issueStatus === RB.BaseComment.STATE_OPEN) {
                    this._openIssueCount++;
                }

                const issueBar = new RB.CommentIssueBarView({
                    el: el,
                    reviewID: this.model.id,
                    commentID: $issueState.data('comment-id'),
                    commentType: $issueState.data('comment-type'),
                    interactive: $issueState.data('interactive'),
                    issueStatus: issueStatus,
                });

                issueBar.render();

                this.listenTo(issueBar, 'statusChanged', newStatus => {
                    if (newStatus === RB.BaseComment.STATE_OPEN) {
                        this._openIssueCount++;
                    } else {
                        this._openIssueCount--;
                    }

                    this.trigger('openIssuesChanged');
                });
            }
        });

        _.each(this.$('.comment-section'), el => {
            const $el = $(el);
            const editor = new RB.ReviewReplyEditor({
                contextID: $el.data('context-id'),
                contextType: $el.data('context-type'),
                review: this.model,
                reviewReply: this._reviewReply,
            });

            this.listenTo(editor, 'change:hasDraft', (model, hasDraft) => {
                if (hasDraft) {
                    this._showReplyDraftBanner();
                    this.trigger('hasDraftChanged', true);
                } else {
                    this._hideReplyDraftBanner();
                }
            });

            const view = new RB.ReviewReplyEditorView({
                el: el,
                model: editor,
                reviewRequestEditor: this.options.reviewRequestEditor,
            });
            view.render();

            this._replyEditors.push(editor);
            this._replyEditorViews.push(view);
        });

        /*
         * Do this last, after ReviewReplyEditorView has already set up the
         * inline editors.
         */
        const reviewRequest = this.model.get('parentObject');
        const bugTrackerURL = reviewRequest.get('bugTrackerURL');
        _.each(this.$('pre.reviewtext'), el => {
            RB.formatText($(el), { bugTrackerURL: bugTrackerURL });
        });

        return this;
    },

    /**
     * Return whether there are any open issues in the review.
     *
     * Returns:
     *     boolean:
     *     true if there are any open issues.
     */
    hasOpenIssues() {
        return this._openIssueCount > 0;
    },

    /**
     * Return the number of open issues in the review.
     *
     * Returns:
     *     number:
     *     The number of open issues.
     */
    getOpenIssueCount() {
        return this._openIssueCount;
    },

    /**
     * Return the ReviewReplyEditorView with the given context type and ID.
     *
     * Args:
     *     contextType (string):
     *         The type of object being replied to (such as ``body_top`` or
     *         ``diff_comments``)
     *
     *     contextID (number, optional):
     *         The ID of the comment being replied to, if appropriate.
     *
     * Returns:
     *     RB.ReviewReplyEditorView:
     *     The matching editor view.
     */
    getReviewReplyEditorView(contextType, contextID) {
        if (contextID === undefined) {
            contextID = null;
        }

        return _.find(this._replyEditorViews, view => {
            const editor = view.model;
            return editor.get('contextID') === contextID &&
                   editor.get('contextType') === contextType;
        });
    },

    /**
     * Return the active reply.
     *
     * Returns:
     *     RB.ReviewReply:
     *     The active draft reply, or null if none exists.
     */
    getReviewReply() {
        return this._reviewReply;
    },

    /**
     * Set up a new ReviewReply for the editors.
     *
     * The new ReviewReply will be used for any new comments made on this
     * review.
     *
     * A ReviewReply is set until it's either destroyed or published, at
     * which point a new one is set.
     *
     * Args:
     *     reviewReply (RB.ReviewReply, optional):
     *         The reply object. If this is ``null``, a new ``RB.ReviewReply``
     *         will be created. Note that this argument is only expected to be
     *         used for unit testing.
     */
    _setupNewReply(reviewReply) {
        if (!reviewReply) {
            reviewReply = this.model.createReply();
        }

        if (this._reviewReply !== null) {
            this.stopListening(this._reviewReply);

            // Update all the existing editors to point to the new object.
            this._replyEditors.forEach(
                editor => editor.set('reviewReply', reviewReply));

            this.trigger('hasDraftChanged', false);
        }

        this.listenTo(reviewReply, 'destroyed published',
                      () => this._setupNewReply());

        this._reviewReply = reviewReply;
    },

    /**
     * Show the reply draft banner.
     *
     * This will be called in response to any new replies made on a review,
     * or if there are pending replies that already exist on the review.
     */
    _showReplyDraftBanner() {
        if (!this._draftBannerShown) {
            this._bannerView = new RB.ReviewReplyDraftBannerView({
                model: this._reviewReply,
                $floatContainer: this.options.$bannerFloatContainer,
                noFloatContainerClass: this.options.bannerNoFloatContainerClass,
                showSendEmail: this.options.showSendEmail,
            });

            this._bannerView.render();
            this._bannerView.$el.appendTo(this.options.$bannerParent);
            this._draftBannerShown = true;
        }
    },

    /**
     * Hide the reply draft banner.
     */
    _hideReplyDraftBanner() {
        if (this._draftBannerShown) {
            this._bannerView.remove();
            this._bannerView = null;
            this._draftBannerShown = false;
        }
    },
});
