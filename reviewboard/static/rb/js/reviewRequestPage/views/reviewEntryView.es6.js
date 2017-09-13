(function() {


const ParentView = RB.ReviewRequestPage.EntryView;


/**
 * Displays a review with discussion on the review request page.
 *
 * Review boxes contain discussion on parts of a review request. This includes
 * comments, screenshots, and file attachments.
 */
RB.ReviewRequestPage.ReviewEntryView = ParentView.extend({
    events: _.defaults({
        'click .revoke-ship-it': '_revokeShipIt',
    }, ParentView.prototype.events),

    /**
     * Initialize the view.
     */
    initialize() {
        ParentView.prototype.initialize.call(this);

        this._reviewView = null;
        this._draftBannerShown = false;
        this._$boxStatus = null;
        this._$fixItLabel = null;
        this._$shipItLabel = null;
    },

    /**
     * Save state before applying an update from the server.
     *
     * This will save all the loaded diff fragments on the entry so that
     * they'll be loaded from cache when processing the fragments again for
     * the entry after reload.
     */
    beforeApplyUpdate() {
        const diffFragmentQueue = RB.PageManager.getPage().diffFragmentQueue;
        const diffCommentsData = this.model.get('diffCommentsData');

        for (let i = 0; i < diffCommentsData.length; i++) {
            diffFragmentQueue.saveFragment(diffCommentsData[i][0]);
        }
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
     *     RB.ReviewRequestPage.ReviewEntryView:
     *     This object, for chaining.
     */
    render() {
        ParentView.prototype.render.call(this);

        this._reviewView = new RB.ReviewRequestPage.ReviewView({
            el: this.el,
            model: this.model.get('review'),
            entryModel: this.model,
            $bannerFloatContainer: this._$box,
            $bannerParent: this.$('.banners'),
            bannerNoFloatContainerClass: 'collapsed',
        });

        this._$boxStatus = this.$('.box-status');
        this._$fixItLabel = this._$boxStatus.find('.fix-it-label');
        this._$shipItLabel = this._$boxStatus.find('.ship-it-label');

        this.listenTo(this._reviewView, 'hasDraftChanged',
                      hasDraft => this.$el.toggleClass('has-draft', hasDraft));
        this.listenTo(this._reviewView, 'openIssuesChanged',
                      this._updateLabels);

        this._reviewView.render();
        this._updateLabels();

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
     *     RB.ReviewRequestPage.ReviewReplyEditorView:
     *     The matching editor view.
     */
    getReviewReplyEditorView(contextType, contextID) {
        return this._reviewView.getReviewReplyEditorView(contextType,
                                                         contextID);
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
        this._updateLabel(this._$fixItLabel,
                          this._reviewView.hasOpenIssues(),
                          'has-issues');
        this._updateLabel(this._$shipItLabel,
                          this.model.get('review').get('shipIt'),
                          'ship-it');
    },

    /**
     * Update the visibility of a label.
     *
     * The label's position and opacity will be set based on whether the
     * label is intended to be visible. The label status box's CSS classes will
     * also be updated based on the visibility and the provided CSS class name.
     *
     * Combined with CSS rules, the label will transition the opacity and
     * the position.
     *
     * Args:
     *     $label (jQuery):
     *         The label element.
     *
     *     visible (boolean):
     *         Whether the label should be shown as visible.
     *
     *     boxClassName (string):
     *         The CSS class to add to or remove from the status box.
     */
    _updateLabel($label, visible, boxClassName) {
        if (visible) {
            this._$boxStatus.addClass(boxClassName);
            $label
                .show()
                .css({
                    opacity: 1,
                    left: 0,
                });
        } else {
            $label.css({
                opacity: 0,
                left: '-100px',
            });
            this._$boxStatus.removeClass(boxClassName);
        }
    },

    /**
     * Revoke the Ship It on the review.
     *
     * This will first confirm that the user does want to revoke the Ship It.
     * If they confirm, the Ship It will be removed via an API call.
     */
    _revokeShipIt() {
        this._$boxStatus.addClass('revoking-ship-it');

        const confirmation =
            RB.ReviewRequestPage.ReviewEntryView.strings.revokeShipItConfirm;

        if (!confirm(confirmation)) {
            this._clearRevokingShipIt();
            return;
        }

        const review = this.model.get('review');

        review.ready({
            ready: () => {
                review.set('shipIt', false);
                review.save({
                    attrs: ['shipIt', 'includeTextTypes'],
                    success: () => {
                        this._updateLabels();

                        /*
                         * Add a delay before removing this, so that the
                         * animation won't be impacted. This will encompass
                         * the length of the animation.
                         */
                        setTimeout(() => this._clearRevokingShipIt(), 900);
                    },
                    error: (model, xhr) => {
                        review.set('shipIt', true);
                        this._clearRevokingShipIt();

                        alert(xhr.responseJSON.err.msg);
                    },
                });
            },
        });
    },

    /**
     * Clear the Revoke Ship It state.
     *
     * This will clear the CSS classes related to the revokation.
     */
    _clearRevokingShipIt() {
        this._$boxStatus.removeClass('revoking-ship-it');
    },
}, {
    strings: {
        revokeShipItConfirm: gettext('Are you sure you want to revoke this Ship It?\n\nThis cannot be undone.'),
    },
});


})();
