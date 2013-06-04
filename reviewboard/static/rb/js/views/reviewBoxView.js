/*
 * Displays a review with discussion on the review request page.
 *
 * Review boxes contain discussion on parts of a review request. This includes
 * comments, screenshots, and file attachments.
 */
RB.ReviewBoxView = RB.CollapsableBoxView.extend({
    initialize: function() {
        this._reviewReply = this.options.reviewReply ||
                            this.model.createReply();
        this._replyEditors = [];
        this._draftBannerShown = false;
        this._$banners = null;
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
            reviewID = review.id;

        RB.CollapsableBoxView.prototype.render.call(this);

        this._$banners = this.$('.banners');

        this._reviewReply.on('destroyed', this._hideReplyDraftBanner, this);

        this.$('pre.reviewtext').each(function() {
            var $el = $(this);

            $el.html(RB.linkifyText($el.text(), bugTrackerURL));
        });

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

            this._replyEditors.push(view);
        }, this);
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
    }
});
