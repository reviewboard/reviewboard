/*
 * Displays a review with discussion on the review request page.
 *
 * Review boxes contain discussion on parts of a review request. This includes
 * comments, screenshots, and file attachments.
 */
RB.ReviewBoxView = RB.CollapsableBoxView.extend({
    initialize: function() {
        this._reviewReply = null;
        this._replyEditors = [];
        this._replyEditorViews = [];
        this._draftBannerShown = false;
        this._$banners = null;
        this._bannerView = null;
        this._$boxStatus = null;
        this._$fixItLabel = null;
        this._openIssueCount = 0;

        this._setupNewReply(this.options.reviewReply);
    },

    /*
     * Renders the review box.
     *
     * This will prepare a reply draft banner, used if the user is replying
     * to any comments on the review.
     *
     * Each comment section will be set up to allow discussion.
     */
    render: function() {
        var reviewRequest = this.model.get('parentObject'),
            pageEditState = this.options.pageEditState,
            bugTrackerURL = reviewRequest.get('bugTrackerURL'),
            review = this.model,
            loadReviewID;

        RB.CollapsableBoxView.prototype.render.call(this);

        // Expand the box if the review is current being linked to
        if (document.URL.indexOf("#review") > -1) {
            loadReviewID = document.URL.split('#review')[1];
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

        _.each(this.$('.review-comments .issue-indicator'), function(el) {
            var $issueState = $('.issue-state', el),
                issueStatus,
                issueBar;

            /*
             * Not all issue-indicator divs have an issue-state div for
             * the issue bar.
             */
            if ($issueState.length > 0) {
                issueStatus = $issueState.data('issue-status');

                if (issueStatus === RB.BaseComment.STATE_OPEN) {
                    this._openIssueCount++;
                }

                issueBar = new RB.CommentIssueBarView({
                    el: el,
                    reviewID: this.model.id,
                    commentID: $issueState.data('comment-id'),
                    commentType: $issueState.data('comment-type'),
                    issueStatus: $issueState.data('issue-status'),
                    interactive: $issueState.data('interactive')
                });

                issueBar.render();

                this.listenTo(issueBar, 'statusChanged',
                              this._onIssueStatusChanged);
            }
        }, this);

        _.each(this.$('.comment-section'), function(el) {
            var $el = $(el),
                editor = new RB.ReviewReplyEditor({
                    contextID: $el.data('context-id'),
                    contextType: $el.data('context-type'),
                    review: review,
                    reviewReply: this._reviewReply
                }),
                view = new RB.ReviewReplyEditorView({
                    el: el,
                    model: editor,
                    pageEditState: pageEditState
                });

            editor.on('change:hasDraft', function(model, hasDraft) {
                if (hasDraft) {
                    this._showReplyDraftBanner();
                }
            }, this);

            view.render();

            this._replyEditors.push(editor);
            this._replyEditorViews.push(view);
        }, this);

        /*
         * Do this last, after ReviewReplyEditorView has already set up the
         * inline editors.
         */
        this.$('pre.reviewtext').each(function() {
            RB.formatText($(this), {
                bugTrackerURL: bugTrackerURL
            });
        });
    },

    /*
     * Returns the ReviewReplyEditorView with the given context type and ID.
     */
    getReviewReplyEditorView: function(contextType, contextID) {
        if (contextID === undefined) {
            contextID = null;
        }

        return _.find(this._replyEditorViews, function(view) {
            var editor = view.model;

            return editor.get('contextID') === contextID &&
                   editor.get('contextType') === contextType;
        });
    },

    /*
     * Shows the reply draft banner.
     *
     * This will be called in response to any new replies made on a review,
     * or if there are pending replies that already exist on the review.
     */
    _showReplyDraftBanner: function() {
        if (!this._draftBannerShown) {
            this._bannerView = new RB.ReviewReplyDraftBannerView({
                model: this._reviewReply,
                $floatContainer: this.$('.box'),
                noFloatContainerClass: 'collapsed',
                showSendEmail: this.options.editorData.showSendEmail
            });

            this._bannerView.render().$el.appendTo(this._$banners);
            this._draftBannerShown = true;
            this.$el.addClass('has-draft');
        }
    },

    /*
     * Hides the reply draft banner.
     */
    _hideReplyDraftBanner: function() {
        if (this._draftBannerShown) {
            this._bannerView.remove();
            this._bannerView = null;
            this._draftBannerShown = false;
            this.$el.removeClass('has-draft');
        }
    },

    /*
     * Sets up a new ReviewReply for the editors.
     *
     * The new ReviewReply will be used for any new comments made on this
     * review.
     *
     * A ReviewReply is set until it's either destroyed or published, at
     * which point a new one is set.
     *
     * A ReviewReply can be provided to this function, and if not supplied,
     * a new one will be created.
     */
    _setupNewReply: function(reviewReply) {
        var hadReviewReply = (this._reviewReply !== null);

        if (!reviewReply) {
            reviewReply = this.model.createReply();
        }

        if (hadReviewReply) {
            this.stopListening(this._reviewReply);

            /*
             * We had one displayed before. Now it's time to clean up and
             * reset all the editors so they're using the old one.
             */
            _.each(this._replyEditors, function(editor) {
                editor.set('reviewReply', reviewReply);
            }, this);

            this._hideReplyDraftBanner();
        }

        this.listenTo(reviewReply, 'destroyed published', function() {
            this._setupNewReply();
        });

        this._reviewReply = reviewReply;
    },

    /*
     * Handler for when the issue status of a comment changes.
     *
     * This will update the number of open issues, and, if there's a
     * Ship It!, will update the label.
     */
    _onIssueStatusChanged: function(issueStatus) {
        if (issueStatus === RB.BaseComment.STATE_OPEN) {
            this._openIssueCount++;
        } else {
            this._openIssueCount--;
        }

        this._updateLabels();
    },

    /*
     * Updates the Ship It and Fix It labels based on the open issue counts.
     *
     * If there are open issues, there will be a "Fix it!" label.
     *
     * If there's a Ship It, there will be a "Ship it!" label.
     *
     * If there's both a Ship It and open issues, the "Fix it!" label will
     * be shown overlaid on top of the "Ship it!" label, and will go away
     * once the issues are resolved.
     */
    _updateLabels: function() {
        if (this._openIssueCount === 0) {
            this._$fixItLabel.css({
                opacity: 0,
                left: '-100px'
            });
            this._$boxStatus.removeClass('has-issues');
        } else {
            this._$boxStatus.addClass('has-issues');
            this._$fixItLabel
                .show()
                .css({
                    opacity: 1,
                    left: 0
                });
        }
    }
});
