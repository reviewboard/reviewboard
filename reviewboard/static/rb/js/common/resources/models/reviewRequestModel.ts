/**
 * A review request.
 */

import {
    type Result,
    Collection,
    spina,
} from '@beanbag/spina';

import { UserSession } from '../../models/userSessionModel';
import { API } from '../../utils/apiUtils';
import {
    type BaseResourceAttrs,
    type BaseResourceResourceData,
    type ResourceLink,
    BaseResource,
} from './baseResourceModel';
import { Diff } from './diffModel';
import { DraftReview } from './draftReviewModel';
import {
    type DraftReviewRequestAttrs,
    DraftReviewRequest,
} from './draftReviewRequestModel';
import {
    type FileAttachmentAttrs,
    FileAttachment,
} from './fileAttachmentModel';
import { type Repository } from './repositoryModel';
import {
    type ReviewAttrs,
    Review,
} from './reviewModel';
import {
    Screenshot,
} from './screenshotModel';


/**
 * Attributes for the ReviewRequest model.
 *
 * Version Added:
 *     7.0
 */
export interface ReviewRequestAttrs extends BaseResourceAttrs {
    /** The reason why the review request is not approved. */
    approvalFailure: string;

    /** Whether the review request is approved. */
    approved: boolean;

    /** The branch field content. */
    branch: string;

    /** The URL template to use for linking to bugs. */
    bugTrackerURL: string;

    /** The list of bugs addressed by this change. */
    bugsClosed: string[];

    /** The commit ID of the change. */
    commitID: string;

    /** The close description for the review request. */
    closeDescription: string;

    /** Whether the ``closeDescription`` field is in Markdown. */
    closeDescriptionRichText: boolean;

    /** A list of other review requests that this one depends on. */
    dependsOn: ResourceLink[];

    /** The review request description */
    description: string;

    /** Whether the ``description`` field is in Markdown. */
    descriptionRichText: boolean;

    /** The current draft review, if any. */
    draftReview: Review;

    /** The last updated timestamp for the review request. */
    lastUpdated: string;

    /** The local site prefix for URLs related to the review request. */
    localSitePrefix: string;

    /** Whether the review request has been published. */
    public: boolean;

    /** The repository for this review request. */
    repository: Repository;

    /** The URL to the review request. */
    reviewURL: string;

    /**
     * The state of the review request.
     *
     * This is one of ``ReviewRequest.CLOSE_DISCARDED``,
     * ``ReviewRequest.CLOSE_SUBMITTED``, or ``ReviewRequest.PENDING``.
     */
    state: number;

    /** The summary for the review request. */
    summary: string;

    /** A list of group names that this review request is assigned to. */
    targetGroups: ResourceLink[];

    /** A list of user names that this review request is assigned to. */
    targetPeople: ResourceLink[];

    /** The testing done field for the review request. */
    testingDone: string;

    /** Whether the ``testingDone`` field is in Markdown. */
    testingDoneRichText: boolean;
}


/**
 * Resource data for the ReviewRequest model.
 *
 * Version Added:
 *     7.0
 */
export interface ReviewRequestResourceData extends BaseResourceResourceData {
    absolute_url: string;
    approvalFailure: string;
    approved: boolean;
    blocks: object[];
    branch: string;
    bugTrackerURL: string;
    bugs_closed: string[];
    depends_on: object[];
    public: boolean;
    raw_text_fields: { [key: string]: string };
    ship_it_count: number;
    status: string;
    summary: string;
    target_groups: object[];
    target_people: object[];
    testing_done: string;
    testing_done_text_type: string;
    time_added: string;
    url: string;
}


/**
 * Options for the ReviewRequest model.
 *
 * Version Added:
 *     7.0
 */
interface ReviewRequestOptions {
    /** Extra attributes to set on the draft object. */
    extraDraftAttrs?: Partial<DraftReviewRequestAttrs>;
}


/**
 * A review request.
 *
 * ReviewRequest is the starting point for much of the resource API. Through
 * it, the caller can create drafts, diffs, file attachments, and screenshots.
 *
 * Fields on a ReviewRequest are set by accessing the ReviewRequest.draft
 * object. Through there, fields can be set like any other model and then
 * saved.
 *
 * A review request can be closed by using the close() function, reopened
 * through reopen(), or even permanently destroyed by calling destroy().
 */
@spina
export class ReviewRequest extends BaseResource<
    ReviewRequestAttrs,
    ReviewRequestResourceData,
    ReviewRequestOptions
> {
    /**
     * Return default values for the model attributes.
     *
     * Returns:
     *     ReviewRequestAttrs:
     *     Default values for the model attributes.
     */
    static defaults(): Result<Partial<ReviewRequestAttrs>> {
        return {
            approvalFailure: null,
            approved: false,
            branch: null,
            bugTrackerURL: null,
            bugsClosed: null,
            closeDescription: null,
            closeDescriptionRichText: false,
            commitID: null,
            dependsOn: [],
            description: null,
            descriptionRichText: false,
            draftReview: null,
            lastUpdated: null,
            localSitePrefix: null,
            'public': null,
            repository: null,
            reviewURL: null,
            state: null,
            summary: null,
            targetGroups: [],
            targetPeople: [],
            testingDone: null,
            testingDoneRichText: false,
        };
    }

    static rspNamespace = 'review_request';

    static extraQueryArgs = {
        'force-text-type': 'html',
        'include-text-types': 'raw',
    };

    static attrToJsonMap: { [key: string]: string } = {
        approvalFailure: 'approval_failure',
        bugsClosed: 'bugs_closed',
        closeDescription: 'close_description',
        closeDescriptionRichText: 'close_description_text_type',
        dependsOn: 'depends_on',
        descriptionRichText: 'description_text_type',
        lastUpdated: 'last_updated',
        reviewURL: 'url',
        targetGroups: 'target_groups',
        targetPeople: 'target_people',
        testingDone: 'testing_done',
        testingDoneRichText: 'testing_done_text_type',
    };

    static deserializedAttrs = [
        'approved',
        'approvalFailure',
        'branch',
        'bugsClosed',
        'closeDescription',
        'dependsOn',
        'description',
        'lastUpdated',
        'public',
        'reviewURL',
        'summary',
        'targetGroups',
        'targetPeople',
        'testingDone',
    ];

    static CHECK_UPDATES_MSECS = 5 * 60 * 1000; // Every 5 minutes

    static CLOSE_DISCARDED = 1;
    static CLOSE_SUBMITTED = 2;
    static PENDING = 3;

    static VISIBILITY_VISIBLE = 1;
    static VISIBILITY_ARCHIVED = 2;
    static VISIBILITY_MUTED = 3;

    /**********************
     * Instance variables *
     **********************/

    /** The current draft of the review request, if any. */
    draft: DraftReviewRequest;

    /** The collection of reviews for this review request. */
    reviews = new Collection<Review>([], {
        model: Review,
    });

    /**
     * Initialize the model.
     *
     * Args:
     *     attrs (object):
     *         Initial values for the model attributes.
     *
     *     options (object):
     *         Additional options for the object construction.
     *
     * Option Args:
     *     extraDraftAttrs (object):
     *         Additional attributes to include when creating a review request
     *         draft.
     */
    initialize(
        attrs?: ReviewRequestAttrs,
        options: Backbone.CombinedModelConstructorOptions<
            ReviewRequestOptions, this> = {}) {
        super.initialize(attrs, options);

        this.draft = new DraftReviewRequest(Object.assign(
            _.pick(this.attributes, [
                'branch',
                'bugsClosed',
                'dependsOn',
                'description',
                'descriptionRichText',
                'summary',
                'targetGroups',
                'targetPeople',
                'testingDone',
                'testingDoneRichText',
            ]),
            { parentObject: this },
            options.extraDraftAttrs));
    }

    /**
     * Return the URL for syncing this model.
     *
     * Returns:
     *     string:
     *     The URL for the API resource.
     */
    url(): string {
        const url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                    'api/review-requests/';

        return this.isNew() ? url : `${url}${this.id}/`;
    }

    /**
     * Create the review request from an existing commit.
     *
     * This can only be used for new ReviewRequest instances, and requires
     * a commitID option.
     *
     * Version Changed:
     *     7.0:
     *     Removed the old callback usage.
     *
     * Version Changed:
     *     5.0:
     *     Changed the arguments to take the commit ID directly, and return a
     *     promise rather than use callbacks.
     *
     * Args:
     *     commitID (string):
     *         A string containing the commit ID to create the review
     *         request from.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    createFromCommit(
        commitID: string,
    ): Promise<JQuery.jqXHR> {
        console.assert(!!commitID);
        console.assert(this.isNew());

        this.set('commitID', commitID);

        return this.save({ createFromCommit: true });
    }

    /**
     * Create a Diff object for this review request.
     *
     * Returns:
     *     RB.Diff:
     *     The new diff model.
     */
    createDiff(): Diff {
        return new Diff({
            parentObject: this,
        });
    }

    /**
     * Create a Review object for this review request.
     *
     * If an ID is specified, the Review object will reference that ID.
     * Otherwise, it is considered a draft review, and will either return
     * the existing one (if the draftReview attribute is set), or create
     * a new one (and set the attribute).
     *
     * Args:
     *     reviewID (number):
     *         The ID of the review, for existing reviews.
     *
     *     extraAttrs (object):
     *         Additional attributes to set on new models.
     *
     * Returns:
     *     RB.Review:
     *     The new review object.
     */
    createReview(
        reviewID?: number,
        extraAttrs: Partial<ReviewAttrs> = {},
    ): Review | DraftReview {
        let review: Review | DraftReview;

        if (reviewID === undefined) {
            review = this.get('draftReview');

            if (review === null) {
                review = new DraftReview({
                    parentObject: this,
                });

                this.set('draftReview', review);
            }
        } else {
            review = this.reviews.get(reviewID);

            if (!review) {
                review = new Review(_.defaults({
                    id: reviewID,
                    parentObject: this,
                }, extraAttrs));
                this.reviews.add(review);
            }

        }

        return review;
    }

    /**
     * Create a Screenshot object for this review request.
     *
     * Args:
     *     screenshotID (number):
     *         The ID of the screenshot, for existing screenshots.
     *
     * Returns:
     *     RB.Screenshot:
     *     The new screenshot object.
     */
    createScreenshot(
        screenshotID: number,
    ): Screenshot {
        return new Screenshot({
            id: screenshotID,
            parentObject: this,
        });
    }

    /**
     * Create a FileAttachment object for this review request.
     *
     * Args:
     *     attributes (object):
     *         Additional attributes to include on the new model.
     *
     * Returns:
     *     RB.FileAttachment:
     *     The new file attachment object.
     */
    createFileAttachment(
        attributes: Partial<FileAttachmentAttrs>,
    ): FileAttachment {
        return new FileAttachment(_.defaults({
            parentObject: this,
        }, attributes));
    }

    /**
     * Mark a review request as starred or unstarred.
     *
     * Version Changed:
     *     7.0:
     *     Got rid of old callbacks-style invocation.
     *
     * Args:
     *     starred (boolean):
     *         Whether the review request is starred.
     *
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async setStarred(
        starred: boolean,
    ): Promise<void> {
        const watched = UserSession.instance.watchedReviewRequests;

        if (starred) {
            await watched.addImmediately(this)
        } else {
            await watched.removeImmediately(this);
        }
    }

    /**
     * Close the review request.
     *
     * A 'type' option must be provided, which must match one of the
     * close types (ReviewRequest.CLOSE_DISCARDED or
     * ReviewRequest.CLOSE_SUBMITTED).
     *
     * An optional description can be set by passing a 'description' option.
     *
     * Version Changed:
     *     7.0:
     *     Got rid of old callbacks-style invocation.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and changed to return a promise.
     *
     * Args:
     *     options (object):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async close(
        options,
    ): Promise<void> {
        const data = {};

        console.assert(options);

        if (options.type === ReviewRequest.CLOSE_DISCARDED) {
            data.status = 'discarded';
        } else if (options.type === ReviewRequest.CLOSE_SUBMITTED) {
            data.status = 'submitted';
        } else {
            return Promise.reject(new Error('Invalid close type'));
        }

        if (options.description !== undefined) {
            data.close_description = options.description;
        }

        if (options.richText !== undefined) {
            data.close_description_text_type =
                (options.richText ? 'markdown' : 'plain');
        }

        if (options.postData !== undefined) {
            _.extend(data, options.postData);
        }

        const changingState = (options.type !== this.get('state'));

        const saveOptions = _.defaults({
            data: data,
        }, options);

        delete saveOptions.type;
        delete saveOptions.description;

        await this.save(saveOptions);

        if (changingState) {
            this.trigger('closed');
        }

        this.markUpdated(this.get('lastUpdated'));
    }

    /**
     * Reopen the review request.
     *
     * Version Changed:
     *     7.0:
     *     Got rid of old callbacks-style invocation.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and changed to return a promise.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async reopen(): Promise<void> {
        await this.save({
            data: {
                status: 'pending',
            },
        });

        this.trigger('reopened');
        this.markUpdated(this.get('lastUpdated'));
    }

    /**
     * Marks the review request as having been updated at the given timestamp.
     *
     * This should be used when an action will trigger an update to the
     * review request's Last Updated timestamp, but where we don't want
     * a notification later on. The local copy of the timestamp can be
     * bumped to mark it as up-to-date.
     *
     * Args:
     *     timestamp (string):
     *         The timestamp to store.
     */
    markUpdated(timestamp: string) {
        this._lastUpdateTimestamp = timestamp;
    }

    /**
     * Begin checking for server-side updates to the review request.
     *
     * The 'updated' event will be triggered when there's a new update.
     *
     * Args:
     *     updateType (string):
     *         The type of updates to check for.
     *
     *     lastUpdateTimestamp (string):
     *         The timestamp of the last known update.
     */
    async beginCheckForUpdates(
        updateType: string,
        lastUpdateTimestamp: string,
    ) {
        this._checkUpdatesType = updateType;
        this._lastUpdateTimestamp = lastUpdateTimestamp;

        await this.ready();
        setTimeout(this._checkForUpdates.bind(this),
                   ReviewRequest.CHECK_UPDATES_MSECS);
    }

    /**
     * Check for updates.
     *
     * This is called periodically after an initial call to
     * beginCheckForUpdates. It will see if there's a new update yet on the
     * server, and if there is, trigger the 'updated' event.
     */
    _checkForUpdates() {
        API.request({
            noActivityIndicator: true,
            prefix: this.get('sitePrefix'),
            success: rsp => {
                const lastUpdate = rsp.last_update;

                if ((!this._checkUpdatesType ||
                     this._checkUpdatesType === lastUpdate.type) &&
                    this._lastUpdateTimestamp !== lastUpdate.timestamp) {
                    this.trigger('updated', lastUpdate);
                }

                this._lastUpdateTimestamp = lastUpdate.timestamp;

                setTimeout(this._checkForUpdates.bind(this),
                           ReviewRequest.CHECK_UPDATES_MSECS);
            },
            type: 'GET',
            url: this.get('links').last_update.href,
        });
    }

    /**
     * Serialize for sending to the server.
     *
     * Args:
     *     options (object):
     *         Options for the save operation.
     *
     * Option Args:
     *     createFromCommit (boolean):
     *         Whether this save is going to create a new review request from
     *         an existing committed change.
     *
     * Returns:
     *     object:
     *     Data suitable for passing to JSON.stringify.
     */
    toJSON(
        options: {
            createFromCommit?: boolean;
        } = {},
    ): object {
        if (this.isNew()) {
            const commitID = this.get('commitID');
            const repository = this.get('repository');
            const result = {};

            if (commitID) {
                result.commit_id = commitID;

                if (options.createFromCommit) {
                    result.create_from_commit_id = true;
                }
            }

            if (repository) {
                result.repository = repository;
            }

            return result;
        } else {
            return super.toJSON(options);
        }
    }

    /**
     * Parse the response from the server.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData(
        rsp: ReviewRequestResourceData,
    ): Partial<ReviewRequestAttrs> {
        const state = {
            discarded: ReviewRequest.CLOSE_DISCARDED,
            pending: ReviewRequest.PENDING,
            submitted: ReviewRequest.CLOSE_SUBMITTED,
        }[rsp.status];
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = super.parseResourceData(rsp);

        data.state = state;
        data.closeDescriptionRichText =
            (rawTextFields['close_description_text_type'] === 'markdown');
        data.descriptionRichText =
            (rawTextFields['description_text_type'] === 'markdown');
        data.testingDoneRichText =
            (rawTextFields['testing_done_text_type'] === 'markdown');

        return data;
    }
}
