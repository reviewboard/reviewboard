(function() {


/**
 * An update bubble showing an update to the review request or a review.
 */
const UpdatesBubbleView = Backbone.View.extend({
    id: 'updates-bubble',

    template: _.template([
        '<span id="updates-bubble-summary"><%- summary %></span>',
        ' by ',
        '<a href="<%- user.url %>" id="updates-bubble-user">',
        '<%- user.fullname || user.username %>',
        '</a>',
        '<span id="updates-bubble-buttons">',
        ' <a href="#" class="update-page"><%- updatePageText %></a>',
        ' | ',
        ' <a href="#" class="ignore"><%- ignoreText %></a>',
    ].join('')),

    events: {
        'click .update-page': '_onUpdatePageClicked',
        'click .ignore': '_onIgnoreClicked',
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     updateInfo (object):
     *         Information about the update, fetched from the server.
     */
    initialize(options) {
        this.options = options;
    },

    /**
     * Render the bubble with the information provided during construction.
     *
     * The bubble starts hidden. The caller must call open() to display it.
     *
     * Returns:
     *     UpdatesBubbleView:
     *     This object, for chaining.
     */
    render() {
        this.$el
            .html(this.template(_.defaults({
                updatePageText: gettext('Update Page'),
                ignoreText: gettext('Ignore'),
            }, this.options.updateInfo)))
            .hide();

        return this;
    },

    /**
     * Open the bubble on the screen.
     */
    open() {
        this.$el
            .css('position', 'fixed')
            .fadeIn();
    },

    /**
     * Close the update bubble.
     *
     * After closing, the bubble will be removed from the DOM.
     */
    close() {
        this.trigger('closed');
        this.$el.fadeOut(_.bind(this.remove, this));
    },

    /**
     * Handle clicks on the "Update Page" link.
     *
     * Loads the review request page.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    _onUpdatePageClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this.trigger('updatePage');
    },

    /*
     * Handle clicks on the "Ignore" link.
     *
     * Ignores the update and closes the page.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    _onIgnoreClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this.close();
    },
});


/**
 * A page managing reviewable content for a review request.
 *
 * This provides common functionality for any page associated with a review
 * request, such as the diff viewer, review UI, or the review request page
 * itself.
 */
RB.ReviewablePageView = RB.PageView.extend({
    events: _.defaults({
        'click #review-action': '_onEditReviewClicked',
        'click #ship-it-action': '_onShipItClicked',
        'click #general-comment-action': '_onAddCommentClicked',
        'click .has-menu .has-menu': '_onMenuClicked',
    }, RB.PageView.prototype.events),

    /**
     * Initialize the page.
     *
     * This will construct a ReviewRequest, CommentIssueManager,
     * ReviewRequestEditor, and other required objects, based on data
     * provided during construction.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     reviewRequestData (object):
     *         The model attributes for a new RB.ReviewRequest instance.
     *
     *     editorData (object):
     *         The model attributes for a new RB.ReviewRequestEditor instance.
     *
     *     lastActivityTimestamp (string):
     *         The last known timestamp for activity on this review request.
     *
     *     checkUpdatesType (string, optional):
     *         The type of updates to check for.
     */
    initialize(options) {
        RB.PageView.prototype.initialize.apply(this, arguments);

        this.options = options;

        RB.DnDUploader.create();

        this.reviewRequestEditorView = new RB.ReviewRequestEditorView({
            el: $('#review-request'),
            model: this.model.reviewRequestEditor,
        });

        this._updatesBubble = null;
        this._favIconURL = null;
        this._favIconNotifyURL = null;
        this._logoNotificationsURL = null;

        /*
         * Some extensions, like Power Pack and rbstopwatch, expect a few legacy
         * attributes on the view. Set these here so these extensions can access
         * them. Note that extensions should ideally use the new form, if
         * they're able to support Review Board 3.0+.
         */
        ['reviewRequest', 'pendingReview'].forEach(attrName => {
            this[attrName] = this.model.get(attrName);

            this.listenTo(this.model, `change:${attrName}`, () => {
                this[attrName] = this.model.get(attrName);
            });
        });

        /*
         * Allow the browser to report notifications, if the user has this
         * enabled.
         */
        RB.NotificationManager.instance.setup();

        if (RB.UserSession.instance.get('authenticated')) {
            this._starManager = new RB.StarManagerView({
                model: new RB.StarManager(),
                el: this.$('.star').parent(),
            });
        }

        this.listenTo(this.model, 'reviewRequestUpdated',
                      this._onReviewRequestUpdated);
    },

    /**
     * Render the page.
     *
     * Returns:
     *     RB.ReviewablePageView:
     *     This object, for chaining.
     */
    render() {
        RB.PageView.prototype.render.call(this);

        const $favicon = $('head').find('link[rel="shortcut icon"]');

        this._favIconURL = $favicon.attr('href');
        this._favIconNotifyURL = STATIC_URLS['rb/images/favicon_notify.ico'];
        this._logoNotificationsURL = STATIC_URLS['rb/images/logo.png'];

        const pendingReview = this.model.get('pendingReview');

        this.draftReviewBanner = RB.DraftReviewBannerView.create({
            el: $('#review-banner'),
            model: pendingReview,
            reviewRequestEditor: this.model.reviewRequestEditor,
        });

        this.listenTo(pendingReview, 'destroy published',
                      () => this.draftReviewBanner.hideAndReload());

        this.reviewRequestEditorView.render();

        return this;
    },

    /**
     * Remove this view from the page.
     */
    remove() {
        this.draftReviewBanner.remove();
        _super(this).remove.call(this);
    },

    /**
     * Catch the review updated event and send the user a visual update.
     *
     * This function will handle the review updated event and decide whether
     * to send a notification depending on browser and user settings.
     *
     * Args:
     *     info (object):
     *         The last update information for the request.
     */
    _onReviewRequestUpdated(info) {
        this._updateFavIcon(this._favIconNotifyURL);

        if (RB.NotificationManager.instance.shouldNotify()) {
            this._showDesktopNotification(info);
        }

        this._showUpdatesBubble(info);
    },

    /**
     * Create the updates bubble showing information about the last update.
     *
     * Args:
     *     info (object):
     *         The last update information for the request.
     */
    _showUpdatesBubble(info) {
        if (this._updatesBubble) {
            this._updatesBubble.remove();
        }

        const reviewRequest = this.model.get('reviewRequest');

        this._updatesBubble = new UpdatesBubbleView({
            updateInfo: info,
            reviewRequest: reviewRequest,
        });

        this.listenTo(this._updatesBubble, 'closed',
                      () => this._updateFavIcon(this._favIconURL));

        this.listenTo(this._updatesBubble, 'updatePage', () => {
            window.location = reviewRequest.get('reviewURL');
        });

        this._updatesBubble.render().$el.appendTo(this.$el);
        this._updatesBubble.open();
    },

    /**
     * Show the user a desktop notification for the last update.
     *
     * This function will create a notification if the user has not
     * disabled desktop notifications and the browser supports HTML5
     * notifications.
     *
     *  Args:
     *     info (object):
     *         The last update information for the request.
     */
    _showDesktopNotification(info) {
        const reviewRequest = this.model.get('reviewRequest');

        RB.NotificationManager.instance.notify({
            title: info.summary,
            body: interpolate(gettext('Review request #%s, by %s'), [
                reviewRequest.id,
                info.user.fullname || info.user.username,
            ]),
            iconURL: this._logoNotificationsURL,
            onClick: () => {
                window.location = reviewRequest.get('reviewURL');
            },
        });
    },

    /**
     * Update the favicon for the page.
     *
     * This is used to change the favicon shown on the page based on whether
     * there's a server-side update notification for the review request.
     */
    _updateFavIcon(url) {
        $('head')
            .find('link[rel="shortcut icon"]')
                .remove()
            .end()
            .append($('<link/>')
                .attr({
                    href: url,
                    rel: 'shortcut icon',
                    type: 'image/x-icon',
                }));
    },

    /**
     * Handle a click on the "Edit Review" button.
     *
     * Displays a review dialog.
     *
     * Returns:
     *    boolean:
     *    false, always.
     */
    _onEditReviewClicked() {
        RB.ReviewDialogView.create({
            review: this.model.get('pendingReview'),
            reviewRequestEditor: this.model.reviewRequestEditor,
        });

        return false;
    },

    /**
     * Handle a click on the "Add Comment" button.
     *
     * Displays a comment dialog.
     *
     * Returns:
     *    boolean:
     *    false, always.
     */
    _onAddCommentClicked() {
        const pendingReview = this.model.get('pendingReview');
        const comment = pendingReview.createGeneralComment(
            undefined,
            RB.UserSession.instance.get('commentsOpenAnIssue'));

        this.listenTo(comment, 'saved',
                      () => RB.DraftReviewBannerView.instance.show());

        RB.CommentDialogView.create({
            comment: comment,
            reviewRequestEditor: this.model.reviewRequestEditor,
        });

        return false;
    },

    /**
     * Handle a click on the "Ship It" button.
     *
     * Confirms that the user wants to post the review, and then posts it
     * and reloads the page.
     *
     * Returns:
     *    boolean:
     *    false, always.
     */
    _onShipItClicked() {
        if (confirm(gettext('Are you sure you want to post this review?'))) {
            this.model.markShipIt();
        }

        return false;
    },

    /**
     * Generic handler for menu clicks.
     *
     * This simply prevents the click from bubbling up or invoking the
     * default action. This function is used for dropdown menu titles
     * so that their links do not send a request to the server when one
     * of their dropdown actions are clicked.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    _onMenuClicked(e) {
        e.preventDefault();
        e.stopPropagation();
    },
});


})();
