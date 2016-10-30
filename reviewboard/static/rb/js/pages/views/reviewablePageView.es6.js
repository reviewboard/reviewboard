{


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
RB.ReviewablePageView = Backbone.View.extend({
    events: {
        'click #review-action': '_onEditReviewClicked',
        'click #ship-it-action': '_onShipItClicked',
        'click #general-comment-action': '_onAddCommentClicked',
    },

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
        this.options = options;

        console.assert(options.reviewRequestData);
        console.assert(options.editorData);

        RB.DnDUploader.create();

        this.reviewRequest = new RB.ReviewRequest(
            this.options.reviewRequestData,
            {
                extraDraftAttrs: this.options.extraReviewRequestDraftData,
            });

        this.pendingReview = this.reviewRequest.createReview();
        this.commentIssueManager = new RB.CommentIssueManager({
            reviewRequest: this.reviewRequest,
        });

        const fileAttachments = _.map(
            this.options.editorData.fileAttachments,
            this.options.editorData.mutableByUser
            ? _.bind(this.reviewRequest.draft.createFileAttachment,
                     this.reviewRequest.draft)
            : _.bind(this.reviewRequest.createFileAttachment,
                     this.reviewRequest));

        this.reviewRequestEditor = new RB.ReviewRequestEditor(
            _.defaults({
                commentIssueManager: this.commentIssueManager,
                reviewRequest: this.reviewRequest,
                fileAttachments: new Backbone.Collection(
                    fileAttachments,
                    { model: RB.FileAttachment }),
            }, this.options.editorData));

        this.reviewRequestEditorView = new RB.ReviewRequestEditorView({
            el: $('#review-request'),
            model: this.reviewRequestEditor,
        });

        this._updatesBubble = null;
        this._favIconURL = null;
        this._favIconNotifyURL = null;
        this._logoNotificationsURL = null;

        RB.NotificationManager.instance.setup();

        if (RB.UserSession.instance.get('authenticated')) {
            this._starManager = new RB.StarManagerView({
                model: new RB.StarManager(),
                el: this.$('.star').parent(),
            });
        }
    },

    /**
     * Render the page.
     *
     * Returns:
     *     RB.ReviewablePageView:
     *     This object, for chaining.
     */
    render() {
        const $favicon = $('head').find('link[rel="shortcut icon"]');

        this._favIconURL = $favicon.attr('href');
        this._favIconNotifyURL = STATIC_URLS['rb/images/favicon_notify.ico'];
        this._logoNotificationsURL = STATIC_URLS['rb/images/logo.png'];

        this.draftReviewBanner = RB.DraftReviewBannerView.create({
            el: $('#review-banner'),
            model: this.pendingReview,
            reviewRequestEditor: this.reviewRequestEditor,
        });

        this.listenTo(this.pendingReview, 'destroy published',
                      () => this.draftReviewBanner.hideAndReload());

        this.reviewRequestEditorView.render();

        this._registerForUpdates();

        // Assign handler for the 'Add File' button
        this.$('#upload-file-action').click(
            _.bind(this._onUploadFileClicked, this));

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
     * Register for update notifications to the review request from the
     * server.
     *
     * The server will be periodically checked for new updates. When a new
     * update arrives, an update bubble will be displayed in the
     * bottom-right of the page, and if the user has allowed desktop
     * notifications in their account settings, a desktop notification
     * will be shown with the update information.
     */
    _registerForUpdates() {
        this.listenTo(this.reviewRequest, 'updated', this._onReviewRequestUpdated);

        this.reviewRequest.beginCheckForUpdates(
            this.options.checkUpdatesType,
            this.options.lastActivityTimestamp);
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
        this._updateFavIcon(this._favIconNotifyURL);

        if (this._updatesBubble) {
            this._updatesBubble.remove();
        }

        this._updatesBubble = new UpdatesBubbleView({
            updateInfo: info,
            reviewRequest: this.reviewRequest,
        });

        this.listenTo(this._updatesBubble, 'closed',
                      () => this._updateFavIcon(this._favIconURL));

        this.listenTo(this._updatesBubble, 'updatePage', () => {
            window.location = this.reviewRequest.get('reviewURL');
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
        this._updateFavIcon(this._favIconNotifyURL);

        RB.NotificationManager.instance.notify({
            'title': interpolate(gettext('Review request submitted by %s'),
                                 [info.user.fullname || info.user.username]),
            'body': null,
            'iconURL': this._logoNotificationsURL,
            'onclick': () => {
                window.location = this.reviewRequest.get('reviewURL');
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
            generalCommentsEnabled:
                this.options.reviewRequestData.generalCommentsEnabled,
            review: this.pendingReview,
            reviewRequestEditor: this.reviewRequestEditor,
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
        const comment = this.pendingReview.createGeneralComment(
            undefined,
            RB.UserSession.instance.get('commentsOpenAnIssue'));

        this.listenTo(comment, 'saved',
                      () => RB.DraftReviewBannerView.instance.show());

        RB.CommentDialogView.create({
            comment: comment,
            reviewRequestEditor: this.reviewRequestEditor,
        });

        return false;
    },

    /**
     * Handle a click on the "Add File" button.
     *
     * Displays popup for attachment upload.
     *
     * Returns:
     *    boolean:
     *    false, always.
     */
    _onUploadFileClicked() {
        const uploadDialog = new RB.UploadAttachmentView({
            reviewRequest: this.reviewRequest,
        });
        uploadDialog.render();

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
            this.pendingReview.ready({
                ready: () => {
                    this.pendingReview.set({
                        shipIt: true,
                        bodyTop: gettext('Ship It!'),
                    });
                    this.pendingReview.publish();
                },
            });
        }

        return false;
    },
});


}
