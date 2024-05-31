/**
 * The draft of a review request.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import { BackboneError } from '../../utils/apiUtils';
import {
    type BaseResourceAttrs,
    type BaseResourceResourceData,
    type ResourceLink,
    type SaveOptions,
    BaseResource,
} from './baseResourceModel';
import { DraftResourceModelMixin } from './draftResourceModelMixin';
import { DraftFileAttachment } from './draftFileAttachmentModel';
import { type FileAttachmentAttrs } from './fileAttachmentModel';
import { type ReviewGroupResourceData } from './reviewGroupModel';
import { type ReviewRequestResourceData } from './reviewRequestModel';
import { type UserResourceData } from './userModel';


/**
 * Attributes for the DraftReviewRequest model.
 *
 * Version Added:
 *     8.0
 */
export interface DraftReviewRequestAttrs extends BaseResourceAttrs {
    /** The branch field content. */
    branch: string;

    /** The list of bugs addressed by this change. */
    bugsClosed: string[];

    /** The change description for the draft. */
    changeDescription: string;

    /** Whether the change description is in Markdown. */
    changeDescriptionRichText: boolean;

    /** A list of other review requests that this one depends on. */
    dependsOn: ResourceLink[] | ReviewRequestResourceData[];

    /** The review request description */
    description: string;

    /** Whether the ``description`` field is in Markdown. */
    descriptionRichText: boolean;

    /** Whether the review request has been published. */
    public: boolean;

    /** The raw versions of the text fields. */
    rawTextFields: Record<string, string> | null;

    /** The owner of the review request. */
    submitter: ResourceLink;

    /** The summary for the review request. */
    summary: string;

    /** A list of group names that this review request is assigned to. */
    targetGroups: ResourceLink[] | ReviewGroupResourceData[];

    /** A list of user names that this review request is assigned to. */
    targetPeople: ResourceLink[] | UserResourceData[];

    /** The testing done field for the review request. */
    testingDone: string;

    /** Whether the ``testingDone`` field is in Markdown. */
    testingDoneRichText: boolean;
}


/**
 * Resource data for the DraftReviewRequest model.
 *
 * Version Added:
 *     8.0
 */
export interface DraftReviewRequestResourceData
extends BaseResourceResourceData {
    branch: string;
    bugs_closed: string[];
    changedescription: string;
    changedescription_text_type: string;
    depends_on: string[];
    description: string;
    description_text_type: string;
    public: boolean;
    raw_text_fields: { [key: string]: string };
    submitter: string;
    summary: string;
    target_groups: string[];
    target_people: string[];
    testing_done: string;
    testing_done_text_type: string;
}


/**
 * Options for the publish operation.
 *
 * Version Added:
 *     7.0
 */
export interface PublishOptions extends SaveOptions {
    /** Whether to suppress e-mail notifications. */
    trivial?: boolean;
}


/**
 * The draft of a review request.
 *
 * This provides editing capabilities for a review request draft, as well
 * as the ability to publish and discard (destroy) a draft.
 */
@spina({
    mixins: [DraftResourceModelMixin],
    prototypeAttrs: ['url'],
})
export class DraftReviewRequest extends BaseResource<
    DraftReviewRequestAttrs,
    DraftReviewRequestResourceData
> {
    static defaults(): Result<Partial<DraftReviewRequestAttrs>> {
        return {
            branch: null,
            bugsClosed: null,
            changeDescription: null,
            changeDescriptionRichText: false,
            dependsOn: [],
            description: null,
            descriptionRichText: false,
            public: null,
            rawTextFields: null,
            submitter: null,
            summary: null,
            targetGroups: [],
            targetPeople: [],
            testingDone: null,
            testingDoneRichText: false,
        };
    }

    static rspNamespace = 'draft';
    static listKey = 'draft';
    static supportsExtraData = true;

    static expandedFields = ['depends_on', 'target_people', 'target_groups'];

    static extraQueryArgs: Result<Record<string, unknown>> = {
        'force-text-type': 'html',
        'include-text-types': 'raw',
    };

    static attrToJsonMap: Record<string, string> = {
        bugsClosed: 'bugs_closed',
        changeDescription: 'changedescription',
        changeDescriptionRichText: 'changedescription_text_type',
        dependsOn: 'depends_on',
        descriptionRichText: 'description_text_type',
        targetGroups: 'target_groups',
        targetPeople: 'target_people',
        testingDone: 'testing_done',
        testingDoneRichText: 'testing_done_text_type',
    };

    static deserializedAttrs = [
        'branch',
        'bugsClosed',
        'changeDescription',
        'dependsOn',
        'description',
        'public',
        'summary',
        'targetGroups',
        'targetPeople',
        'testingDone',
    ];

    /**********************
     * Instance variables *
     **********************/

    /** Tell DraftResourceModelMixin not to override our url() method. */
    _hasOwnURL = true;

    /**
     * Return the URL to use when syncing the model.
     *
     * Returns:
     *     string:
     *     The URL to sync.
     */
    url(): string {
        return this.get('parentObject').get('links').draft.href;
    }

    /**
     * Create a FileAttachment object for this draft.
     *
     * Args:
     *     attributes (object):
     *         Attributes for the file attachment model.
     *
     * Returns:
     *     RB.DraftFileAttachment:
     *     The new file attachment object.
     */
    createFileAttachment(
        attributes: FileAttachmentAttrs,
    ): DraftFileAttachment {
        return new DraftFileAttachment(Object.assign(
            { parentObject: this },
            attributes));
    }

    /**
     * Publish the draft.
     *
     * The contents of the draft will be validated before being sent to the
     * server in order to ensure that the appropriate fields are all there.
     *
     * Version Changed:
     *     8.0:
     *     Removed callbacks and the context parameter.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated the callbacks and added a promise return value.
     *
     * Args:
     *     options (object, optional):
     *         Options for the operation, including callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async publish(
        options: PublishOptions = {},
    ): Promise<void> {
        console.assert(
            !(options.success || options.error || options.complete),
            dedent`
                RB.DraftReviewRequest.publish was called using callbacks. This
                has been removed in Review Board 8.0 in favor of promises.
            `);

        await this.ready();

        const validationError = this.validate(this.attributes);

        if (validationError) {
            throw new BackboneError(
                this, { errorText: validationError }, options);
        }

        await this.save(Object.assign(
            {
                data: {
                    public: 1,
                    trivial: options.trivial ? 1 : 0,
                },
            },
            options));
    }

    /**
     * Parse resource data from the server.
     *
     * Args:
     *     rsp (DraftReviewRequestResourceData):
     *          The response data from the server.
     *
     * Returns:
     *     DraftReviewRequestAttrs:
     *     Attributes to set on the model.
     */
    parseResourceData(
        rsp: Partial<DraftReviewRequestResourceData>,
    ): Partial<DraftReviewRequestAttrs> {
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = super.parseResourceData(rsp);

        data.submitter = rsp.links.submitter;
        data.changeDescriptionRichText =
            (rawTextFields.changedescription_text_type === 'markdown');
        data.descriptionRichText =
            (rawTextFields.description_text_type === 'markdown');
        data.testingDoneRichText =
            (rawTextFields.testing_done_text_type === 'markdown');
        data.rawTextFields = rawTextFields || null;

        return data;
    }
}
