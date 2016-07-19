(function() {


/*
 * An update bubble showing an update to the review request or a review.
 */
var UpdatesBubbleView = Backbone.View.extend({
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
        ' <a href="#" class="ignore"><%- ignoreText %></a>'
    ].join('')),

    events: {
        'click .update-page': '_onUpdatePageClicked',
        'click .ignore': '_onIgnoreClicked'
    },

    /*
     * Renders the bubble with the information provided during construction.
     *
     * The bubble starts hidden. The caller must call open() to display it.
     */
    render: function() {
        this.$el
            .html(this.template(_.defaults({
                updatePageText: gettext('Update Page'),
                ignoreText: gettext('Ignore')
            }, this.options.updateInfo)))
            .hide();

        return this;
    },

    /*
     * Opens the bubble on the screen.
     */
    open: function() {
        this.$el
            .css('position', 'fixed')
            .fadeIn();
    },

    /*
     * Closes the update bubble.
     *
     * After closing, the bubble will be removed from the DOM.
     */
    close: function() {
        this.trigger('closed');
        this.$el.fadeOut(_.bind(this.remove, this));
    },

    /*
     * Handler for when the "Update Page" link is clicked.
     *
     * Loads the review request page.
     */
    _onUpdatePageClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this.trigger('updatePage');
    },

    /*
     * Handler for when the "Ignore" link is clicked.
     *
     * Ignores the update and closes the page.
     */
    _onIgnoreClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this.close();
    }
});


/*
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
        'click #general-comment-action': '_onAddCommentClicked'
    },

    /*
     * Initializes the page.
     *
     * This will construct a ReviewRequest, CommentIssueManager,
     * ReviewRequestEditor, and other required objects, based on data
     * provided during construction.
     *
     * This requires the following options:
     *
     *     * reviewRequestData
     *       - The model attributes that will populate a ReviewRequest.
     *
     *     * editorData
     *       - The model attributes that will populate a ReviewRequestEditor.
     *
     *     * lastActivityTimestamp
     *       - The last known timestamp indicating activity on this
     *         review request.
     *
     * The following options are optional:
     *
     *     * checkUpdatesType
     *       - The type of updates to look for.
     */
    initialize: function() {
        var fileAttachments;

        console.assert(this.options.reviewRequestData);
        console.assert(this.options.editorData);

        RB.DnDUploader.create();

        this.reviewRequest = new RB.ReviewRequest(
            this.options.reviewRequestData,
            {
                extraDraftAttrs: this.options.extraReviewRequestDraftData
            });

        this.pendingReview = this.reviewRequest.createReview();
        this.commentIssueManager = new RB.CommentIssueManager({
            reviewRequest: this.reviewRequest
        });

        fileAttachments = _.map(
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
                    { model: RB.FileAttachment })
            }, this.options.editorData));

        this.reviewRequestEditorView = new RB.ReviewRequestEditorView({
            el: $('#review_request'),
            model: this.reviewRequestEditor
        });

        this._updatesBubble = null;
        this._favIconURL = null;
        this._favIconNotifyURL = null;
        this._logoNotificationsURL = null;

        RB.NotificationManager.instance.setup();

        if (RB.UserSession.instance.get('authenticated')) {
            this._starManager = new RB.StarManagerView({
                model: new RB.StarManager(),
                el: this.$('.star').parent()
            });
        }
    },

    /*
     * Renders the page.
     */
    render: function() {
        var $favicon = $('head').find('link[rel="shortcut icon"]');

        this._favIconURL = $favicon.attr('href');
        this._favIconNotifyURL = STATIC_URLS['rb/images/favicon_notify.ico'];
        this._logoNotificationsURL = STATIC_URLS['rb/images/logo.png'];

        this.draftReviewBanner = RB.DraftReviewBannerView.create({
            el: $('#review-banner'),
            model: this.pendingReview,
            reviewRequestEditor: this.reviewRequestEditor
        });

        this.listenTo(this.pendingReview, 'destroy published', function() {
            this.draftReviewBanner.hideAndReload();
        });

        this.reviewRequestEditorView.render();

        this._registerForUpdates();

        // Assign handler for the 'Add File' button
        this.$('#upload-file-action').click(
            _.bind(this._onUploadFileClicked, this));

        return this;
    },

    remove: function() {
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
    _registerForUpdates: function() {
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
     *     info (Object):
     *         The last update information for the request.
     */
    _onReviewRequestUpdated: function(info) {
        if (RB.NotificationManager.instance.shouldNotify()) {
            this._showDesktopNotification(info);
        }

        this._showUpdatesBubble(info);
    },

    /*
     * Create the updates bubble showing information about the last update.
     *
     * Args:
     *     info (Object):
     *         The last update information for the request.
     */
    _showUpdatesBubble: function(info) {
        this._updateFavIcon(this._favIconNotifyURL);

        if (this._updatesBubble) {
            this._updatesBubble.remove();
        }

        this._updatesBubble = new UpdatesBubbleView({
            updateInfo: info,
            reviewRequest: this.reviewRequest
        });

        this.listenTo(this._updatesBubble, 'closed', function() {
            this._updateFavIcon(this._favIconURL);
        });

        this.listenTo(this._updatesBubble, 'updatePage', function() {
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
     *     info (Object):
     *         The last update information for the request.
     */
     _showDesktopNotification: function(info) {
        var username = info.user.fullname || info.user.username,
            notificationText = gettext('Review request submitted by %s'),
            onclick = _.bind(function() {
                window.location = this.reviewRequest.get('reviewURL');
            }, this);

        this._updateFavIcon(this._favIconNotifyURL);

        notificationData = {
            'title': interpolate(notificationText, [username]),
            'body': null,
            'iconURL': this._logoNotificationsURL,
            'onclick': onclick
        };

        RB.NotificationManager.instance.notify(notificationData);
     },

    /**
     * Update the favicon for the page.
     *
     * This is used to change the favicon shown on the page based on whether
     * there's a server-side update notification for the review request.
     */
    _updateFavIcon: function(url) {
        $('head')
            .find('link[rel="shortcut icon"]')
                .remove()
            .end()
            .append($('<link/>')
                .attr({
                    href: url,
                    rel: 'shortcut icon',
                    type: 'image/x-icon'
                }));
    },

    /*
     * Handler for when Edit Review is clicked.
     *
     * Displays a review dialog.
     */
    _onEditReviewClicked: function() {
        RB.ReviewDialogView.create({
            review: this.pendingReview,
            reviewRequestEditor: this.reviewRequestEditor
        });

        return false;
    },

    /*
     * Handler for when Add Comment is clicked.
     *
     * Displays a comment dialog.
     */
    _onAddCommentClicked: function() {
        var comment = this.pendingReview.createGeneralComment(
            undefined,
            RB.UserSession.instance.get('commentsOpenAnIssue')
        );

        comment.on('saved',function(){
            RB.DraftReviewBannerView.instance.show();
        }, this);

        RB.CommentDialogView.create({
            comment: comment,
            reviewRequestEditor: this.reviewRequestEditor
        });

        return false;
    },

    /*
     * Handler for when the "Add File" link is clicked.
     *
     * Displays popup for attachment upload.
     */
    _onUploadFileClicked: function() {
        var uploadDialog = new RB.UploadAttachmentView({
            reviewRequest: this.reviewRequest
        });
        uploadDialog.render();
    },

    /*
     * Handler for when Ship It is clicked.
     *
     * Confirms that the user wants to post the review, and then posts it
     * and reloads the page.
     */
    _onShipItClicked: function() {
        if (confirm(gettext('Are you sure you want to post this review?'))) {
            this.pendingReview.ready({
                ready: function() {
                    this.pendingReview.set({
                        shipIt: true,
                        bodyTop: gettext('Ship It!')
                    });
                    this.pendingReview.publish();
                }
            }, this);
        }

        return false;
    }
});


})();
