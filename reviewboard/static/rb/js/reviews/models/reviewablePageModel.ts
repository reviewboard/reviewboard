/**
 * A page used for editing, viewing, or reviewing review requests.
 */
import { ModelAttributes, spina } from '@beanbag/spina';

import {
    FileAttachment,
    Page,
    ResourceCollection,
    Review,
} from 'reviewboard/common';

import {
    ReviewRequestEditor,
    ReviewRequestEditorAttrs,
} from './reviewRequestEditorModel';


/** Attributes for the ReviewablePage model. */
export interface ReviewablePageAttrs extends ModelAttributes {
    /** Whether the page should periodically check the server for updates. */
    checkForUpdates?: boolean;

    /**
     * A type identifier used to represent the page for any update checks.
     *
     * This corresponds to strings used server-side. Arbitrary values have
     * undefined behavior.
     */
    checkUpdatesType?: string;

    /** Data to pass into the review request editor. */
    editorData?: Partial<ReviewRequestEditorAttrs>;

    /**
     * A string-encoded timestamp for the last activity on the review request.
     */
    lastActivityTimestamp?: string;

    /**
     * The pending review used for any new review content.
     *
     * This may or may not yet have a server-side representation.
     */
    pendingReview?: Review;

    /**
     * The review request that this page is for.
     */
    reviewRequest?: RB.ReviewRequest;
}


/** The format of data passed in to the object. */
export interface ReviewablePageParseData {
    reviewRequestData: {
        state: string,
        visibility: string,
        localSitePrefix: string,
        repository: object,
    };
    extraReviewRequestDraftData: object;
    checkForUpdates: boolean;
    checkUpdatesType: string;
    lastActivityTimestamp: string;
}


/**
 * A page used for editing, viewing, or reviewing review requests.
 *
 * This is responsible for setting up objects needed for manipulating a
 * review request or related state, for performing reviews, or otherwise
 * handling review-related tasks.
 *
 * This can be used directly or can be subclassed in order to provide
 * additional logic.
 */
@spina
export class ReviewablePage<
    TDefaults extends ReviewablePageAttrs = ReviewablePageAttrs,
    TExtraModelOptions = unknown
> extends Page<TDefaults, TExtraModelOptions> {
    static defaults: ReviewablePageAttrs = {
        checkForUpdates: false,
        checkUpdatesType: null,
        lastActivityTimestamp: null,
        pendingReview: null,
        reviewRequest: null,
    };

    /**********************
     * Instance variables *
     **********************/

    /** Manages the issue states for published comments. */
    commentIssueManager: RB.CommentIssueManager;

    /** Manages the edit states and capabilities for the review request. */
    reviewRequestEditor: ReviewRequestEditor;

    /**
     * Initialize the page.
     *
     * This will construct a series of objects needed to work with reviews
     * and the review request. It will also begin checking for updates made
     * to the page, notifying the user if anything has changed.
     *
     * Args:
     *     attributes (ReviewablePageAttrs):
     *         Initial attributes passed to the constructor. This is used to
     *         access initial state that won't otherwise be stored in this
     *         page.
     *
     *     options (object):
     *         Options for the page.
     */
    initialize(
        attributes: TDefaults,
        options: TExtraModelOptions,
    ) {
        super.initialize(attributes, options);

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
        const reviewRequestOrDraft = (editorData.mutableByUser
                                      ? reviewRequest.draft
                                      : reviewRequest);
        const fileAttachments = new ResourceCollection<FileAttachment>(
            _.map(editorData.fileAttachments,
                  attrs => reviewRequestOrDraft.createFileAttachment(attrs)),
            {
                model: FileAttachment,
                parentResource: reviewRequestOrDraft,
            });
        const allFileAttachments = new ResourceCollection<FileAttachment>(
            _.map(editorData.allFileAttachments,
                  attrs => reviewRequestOrDraft.createFileAttachment(attrs)),
            {
                model: FileAttachment,
                parentResource: reviewRequestOrDraft,
            });

        this.reviewRequestEditor = new ReviewRequestEditor(
            _.defaults({
                allFileAttachments: allFileAttachments,
                commentIssueManager: this.commentIssueManager,
                fileAttachments: fileAttachments,
                reviewRequest: reviewRequest,
            }, editorData),
            { parse: true });

        this.listenTo(reviewRequest, 'updated',
                      info => this.trigger('reviewRequestUpdated', info));

        if (this.get('checkForUpdates')) {
            this._registerForUpdates();
        }
    }

    /**
     * Post a review marked as Ship It.
     *
     * This will create and publish a review, setting the Ship It state and
     * changing the text to say "Ship It!".
     */
    async markShipIt() {
        const pendingReview = this.get('pendingReview');

        await pendingReview.ready();

        pendingReview.set({
            bodyTop: _`Ship It!`,
            shipIt: true,
        });
        await pendingReview.publish();
    }

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
    parse(
        rsp: ReviewablePageParseData,
    ): ReviewablePageAttrs {
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
            checkForUpdates: rsp.checkForUpdates,
            checkUpdatesType: rsp.checkUpdatesType,
            lastActivityTimestamp: rsp.lastActivityTimestamp,
            pendingReview: reviewRequest.createReview(),
            reviewRequest: reviewRequest,
        };
    }

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
    }
}
