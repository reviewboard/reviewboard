/**
 * A page used for editing, viewing, or reviewing review requests.
 *
 * This is responsible for setting up objects needed for manipulating a
 * review request or related state, for performing reviews, or otherwise
 * handling review-related tasks.
 *
 * This can be used directly or can be subclassed in order to provide
 * additional logic.
 *
 * Attributes:
 *     commentIssueManager (RB.CommentIssueManager):
 *         Manages the issue states for published comments.
 *
 *     reviewRequestEditor (RB.ReviewRequestEditor):
 *         Manages the edit states and capabilities for the review request
 *         for the page.
 *
 * Model Attributes:
 *     checkForUpdates (boolean):
 *         Whether the page should periodically check the server for updates
 *         made to the page.
 *
 *     checkUpdatesType (string):
 *         A type identifier used to represent the page for any update checks.
 *         This corresponds to strings used server-side. Arbitrary values
 *         have undefined behavior.
 *
 *     lastActivityTimestamp (string):
 *         A string-encoded timestamp representing the last time there was
 *         known activity on the review request.
 *
 *     pendingReview (RB.Review):
 *         The pending review (which may or may not yet have a server-side
 *         representation) used for any new review content.
 *
 *     reviewRequest (RB.ReviewRequest):
 *         The review request that this page is for.
 */
RB.ReviewablePage = RB.Page.extend({
    defaults: _.defaults({
        checkForUpdates: false,
        checkUpdatesType: null,
        lastActivityTimestamp: null,
        pendingReview: null,
        reviewRequest: null,
    }, RB.Page.prototype.defaults),

    /**
     * Initialize the page.
     *
     * This will construct a series of objects needed to work with reviews
     * and the review request. It will also begin checking for updates made
     * to the page, notifying the user if anything has changed.
     *
     * Args:
     *     attributes (object):
     *         Initial attributes passed to the constructor. This is used to
     *         access initial state that won't otherwise be stored in this
     *         page.
     */
    initialize(attributes) {
        RB.Page.prototype.initialize.apply(this, arguments);

        const reviewRequest = this.get('reviewRequest');

        console.assert(
            reviewRequest,
            'The reviewRequest attribute or parse=true must be provided.');
        console.assert(
            this.get('pendingReview'),
            'The pendingReview attribute or parse=true must be provided.');

        this.commentIssueManager = new RB.CommentIssueManager({
            reviewRequest: reviewRequest,
        });

        const editorData = attributes.editorData || {};
        const fileAttachments = new Backbone.Collection(
            _.map(editorData.fileAttachments,
                  (editorData.mutableByUser
                   ? attrs => reviewRequest.draft.createFileAttachment(attrs)
                   : attrs => reviewRequest.createFileAttachment(attrs))),
            {
                model: RB.FileAttachment,
            });

        this.reviewRequestEditor = new RB.ReviewRequestEditor(
            _.defaults({
                commentIssueManager: this.commentIssueManager,
                reviewRequest: reviewRequest,
                fileAttachments: fileAttachments,
            }, editorData),
            {parse: true});

        this.listenTo(reviewRequest, 'updated',
                      info => this.trigger('reviewRequestUpdated', info));

        if (this.get('checkForUpdates')) {
            this._registerForUpdates();
        }
    },

    /**
     * Post a review marked as Ship It.
     *
     * This will create and publish a review, setting the Ship It state and
     * changing the text to say "Ship It!".
     */
    markShipIt() {
        const pendingReview = this.get('pendingReview');

        pendingReview.ready({
            ready() {
                pendingReview.set({
                    shipIt: true,
                    bodyTop: gettext('Ship It!'),
                });
                pendingReview.publish();
            },
        });
    },

    /**
     * Parse the data for the page.
     *
     * This will take data from the server and turn it into a series of
     * objects and attributes needed for parts of the page.
     *
     * Args:
     *     rsp (object):
     *         The incoming data provided for the page.
     *
     * Returns:
     *     object:
     *     The resulting attributes for the page.
     */
    parse(rsp) {
        let reviewRequestData;

        if (rsp.reviewRequestData) {
            reviewRequestData = _.defaults({
                state: RB.ReviewRequest[rsp.reviewRequestData.state],
                visibility: RB.ReviewRequest['VISIBILITY_' +
                                             rsp.reviewRequestData.visibility],
            }, rsp.reviewRequestData);

            if (reviewRequestData.repository) {
                reviewRequestData.repository = new RB.Repository(
                    _.defaults({
                        localSitePrefix: rsp.reviewRequestData.localSitePrefix,
                    }, rsp.reviewRequestData.repository));
            }
        }

        const reviewRequest = new RB.ReviewRequest(
            reviewRequestData,
            {
                extraDraftAttrs: rsp.extraReviewRequestDraftData,
            });

        return {
            reviewRequest: reviewRequest,
            pendingReview: reviewRequest.createReview(),
            lastActivityTimestamp: rsp.lastActivityTimestamp,
            checkForUpdates: rsp.checkForUpdates,
            checkUpdatesType: rsp.checkUpdatesType,
        };
    },

    /**
     * Register for update notification to the review request from the server.
     *
     * The server will be periodically checked for new updates. When a new
     * update arrives, an update bubble will be displayed in the bottom-right
     * of the page, and if the user has allowed desktop notifications in their
     * account settings, a desktop notification will be shown with the update
     * information.
     */
    _registerForUpdates() {
        this.get('reviewRequest').beginCheckForUpdates(
            this.get('checkUpdatesType'),
            this.get('lastActivityTimestamp'));
    },
});
