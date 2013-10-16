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
            review = this.model;

        RB.CollapsableBoxView.prototype.render.call(this);

        this._$banners = this.$('.banners');

        this._reviewReply.on('destroyed published', function() {
            this._setupNewReply();
        }, this);

        _.each(this.$('.review-comments .issue-indicator'), function(el) {
            var $issueState = $('.issue-state', el),
                issueBar;

            /*
             * Not all issue-indicator divs have an issue-state div for
             * the issue bar.
             */
            if ($issueState.length > 0) {
                issueBar = new RB.CommentIssueBarView({
                    el: el,
                    reviewID: this.model.id,
                    commentID: $issueState.data('comment-id'),
                    commentType: $issueState.data('comment-type'),
                    issueStatus: $issueState.data('issue-status'),
                    interactive: $issueState.data('interactive')
                });

                issueBar.render();
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
            var $el = $(this);

            RB.formatText($el, $el.text(), bugTrackerURL, {
                forceRichText: true
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
            var banner = new RB.ReviewReplyDraftBannerView({
                model: this._reviewReply,
                $floatContainer: this.$('.box'),
                noFloatContainerClass: 'collapsed'
            });

            banner.render().$el.appendTo(this._$banners);
            this._draftBannerShown = true;
        }
    },

    /*
     * Hides the reply draft banner.
     */
    _hideReplyDraftBanner: function() {
        this._$banners.children().remove();
        this._draftBannerShown = false;
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

        reviewReply.on('destroyed published', this._setupNewReply, this);

        if (hadReviewReply) {
            this._reviewReply.off(null, null, this);

            /*
             * We had one displayed before. Now it's time to clean up and
             * reset all the editors so they're using the old one.
             */
            _.each(this._replyEditors, function(editor) {
                editor.set('reviewReply', reviewReply);
            }, this);

            this._hideReplyDraftBanner();
        }

        this._reviewReply = reviewReply;
    }
});
