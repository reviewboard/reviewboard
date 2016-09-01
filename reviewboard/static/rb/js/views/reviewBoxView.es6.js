/**
 * Displays a review with discussion on the review request page.
 *
 * Review boxes contain discussion on parts of a review request. This includes
 * comments, screenshots, and file attachments.
 */
RB.ReviewBoxView = RB.CollapsableBoxView.extend({
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
     *
     *     showSendEmail (boolean):
     *         Whether to show the "Send E-mail" box on replies.
     */
    initialize(options) {
        RB.CollapsableBoxView.prototype.initialize.call(this, options);

        this._reviewReply = null;
        this._replyEditors = [];
        this._replyEditorViews = [];
        this._draftBannerShown = false;
        this._$banners = null;
        this._bannerView = null;
        this._$boxStatus = null;
        this._$fixItLabel = null;
        this._openIssueCount = 0;

        this._setupNewReply();
    },

    /**
     * Render the review box.
     *
     * This will prepare a reply draft banner, used if the user is replying
     * to any comments on the review.
     *
     * Each comment section will be set up to allow discussion.
     *
     * Returns:
     *     RB.ReviewBoxView:
     *     This object, for chaining.
     */
    render() {
        const reviewRequest = this.model.get('parentObject');

        RB.CollapsableBoxView.prototype.render.call(this);

        // Expand the box if the review is current being linked to
        if (document.URL.indexOf("#review") > -1) {
            const loadReviewID = document.URL.split('#review')[1];

            if (parseInt(loadReviewID, 10) === this.model.id) {
                this._$box.removeClass('collapsed');
                this._$expandCollapseButton
                    .removeClass('rb-icon-expand-review')
                    .addClass('rb-icon-collapse-review');
            }
        }

        this._$banners = this.$('.banners');
        this._$boxStatus = this.$('.box-status');
        this._$fixItLabel = this._$boxStatus.find('.fix-it-label');

        _.each(this.$('.review-comments .issue-indicator'), el => {
            const $issueState = $('.issue-state', el);

            /*
             * Not all issue-indicator divs have an issue-state div for
             * the issue bar.
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
                    issueStatus: $issueState.data('issue-status'),
                    interactive: $issueState.data('interactive'),
                });

                issueBar.render();

                this.listenTo(issueBar, 'statusChanged',
                              this._onIssueStatusChanged);
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
        const bugTrackerURL = reviewRequest.get('bugTrackerURL');
        _.each(this.$('pre.reviewtext'), el => {
            RB.formatText($(el), { bugTrackerURL: bugTrackerURL });
        });

        return this;
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
     * Show the reply draft banner.
     *
     * This will be called in response to any new replies made on a review,
     * or if there are pending replies that already exist on the review.
     */
    _showReplyDraftBanner() {
        if (!this._draftBannerShown) {
            this._bannerView = new RB.ReviewReplyDraftBannerView({
                model: this._reviewReply,
                $floatContainer: this._$box,
                noFloatContainerClass: 'collapsed',
                showSendEmail: this.options.showSendEmail,
            });

            this._bannerView.render().$el.appendTo(this._$banners);
            this._draftBannerShown = true;
            this.$el.addClass('has-draft');
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
            this.$el.removeClass('has-draft');
        }
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
     *         will be created.
     */
    _setupNewReply(reviewReply) {
        const hadReviewReply = (this._reviewReply !== null);

        if (!reviewReply) {
            reviewReply = this.model.createReply();
        }

        if (hadReviewReply) {
            this.stopListening(this._reviewReply);

            /*
             * We had one displayed before. Now it's time to clean up and
             * reset all the editors so they're using the old one.
             */
            this._replyEditors.forEach(
                editor => editor.set('reviewReply', reviewReply));

            this._hideReplyDraftBanner();
        }

        this.listenTo(reviewReply, 'destroyed published',
                      () => this._setupNewReply());

        this._reviewReply = reviewReply;
    },

    /**
     * Handle when the issue status of a comment changes.
     *
     * This will update the number of open issues, and, if there's a
     * Ship It!, will update the label.
     *
     * Args:
     *     issueStatus (string):
     *         The new issue status.
     */
    _onIssueStatusChanged(issueStatus) {
        if (issueStatus === RB.BaseComment.STATE_OPEN) {
            this._openIssueCount++;
        } else {
            this._openIssueCount--;
        }

        this._updateLabels();
    },

    /**
     * Update the "Ship It" and "Fix It" labels based on the open issue counts.
     *
     * If there are open issues, there will be a "Fix it!" label.
     *
     * If there's a Ship It, there will be a "Ship it!" label.
     *
     * If there's both a Ship It and open issues, the "Fix it!" label will
     * be shown overlaid on top of the "Ship it!" label, and will go away
     * once the issues are resolved.
     */
    _updateLabels() {
        if (this._openIssueCount === 0) {
            this._$fixItLabel.css({
                opacity: 0,
                left: '-100px',
            });
            this._$boxStatus.removeClass('has-issues');
        } else {
            this._$boxStatus.addClass('has-issues');
            this._$fixItLabel
                .show()
                .css({
                    opacity: 1,
                    left: 0,
                });
        }
    },
});
