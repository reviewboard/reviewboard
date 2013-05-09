/*
 * Displays a review with discussion on the review request page.
 *
 * Review boxes contain discussion on parts of a review request. This includes
 * comments, screenshots, and file attachments.
 */
RB.ReviewBoxView = Backbone.View.extend({
    events: {
        'click .collapse-button': '_onToggleCollapseClicked'
    },

    initialize: function() {
        this._reviewReply = this.options.reviewReply ||
                            this.model.createReply();
        this._replyEditors = [];
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

        this._$box = this.$('.box');
        this._$banners = this.$('.banners');
        this._$bannerButtons = this._$banners.find('input');

        this._reviewReply.on('saving destroying', function() {
            this._$bannerButtons.prop('disabled', true);
        }, this);

        this._reviewReply.on('saved', function() {
            this._$bannerButtons.prop('disabled', false);
        }, this);

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
     * Expands the box.
     */
    expand: function() {
        this._$box.removeClass('collapsed');
    },

    /*
     * Collapses the box.
     */
    collapse: function() {
        this._$box.addClass('collapsed');
    },

    /*
     * Shows the reply draft banner.
     *
     * This will be called in response to any new replies made on a review,
     * or if there are pending replies that already exist on the review.
     */
    _showReplyDraftBanner: function() {
        if (!this._draftBannerShown) {
            this._$banners.append($.replyDraftBanner(this._reviewReply,
                                                     this._$bannerButtons));
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
     * Handler for when the Expand/Collapse button is clicked.
     *
     * Toggles the collapsed state of the box.
     */
    _onToggleCollapseClicked: function() {
        if (this._$box.hasClass('collapsed')) {
            this.expand();
        } else {
            this.collapse();
        }
    }
});
