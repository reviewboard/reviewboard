/**
 * A review.
 */

import { spina } from '@beanbag/spina';

import * as JSONSerializers from '../utils/serializers';
import { BaseResource, BaseResourceAttrs } from './baseResourceModel';
import { ReviewReply } from './reviewReplyModel';


/**
 * Attributes for the review model.
 *
 * Version Added:
 *     6.0
 */
export interface ReviewAttrs extends BaseResourceAttrs {
    /** The name of the review author. */
    authorName: string;

    /** The contents of the footer that shows up below all comments. */
    bodyBottom: string;

    /** Whether the ``bodyBottom`` field should be rendered as Markdown. */
    bodyBottomRichText: boolean;

    /** The contents of the header that shows up above all comments. */
    bodyTop: string;

    /** Whether the ``bodyTop`` field should be rendered as Markdown. */
    bodyTopRichText: boolean;

    /** The draft reply to this review, if any. */
    draftReply: ReviewReply;

    /** The text format type to request for text fields in all responses. */
    forceTextType: string;

    /**
     * The contents of any HTML-rendered text fields.
     *
     * This is set if the caller fetches or posts with
     * ``includeTextTypes=html``. The keys in this object are the field names,
     * and the values are the rendered HTML versions of the field values.
     */
    htmlTextFields: { [key: string]: string };

    /**
     * A comma-separated list of text types to include when syncing the model.
     */
    includeTextTypes: string;

    /**
     * The source contents of any Markdown-rendered text fields.
     *
     * This is set if the caller fetches or posts with
     * ``includeTextTypes=markdown``. The keys in this object are the field
     * names, and the values are the Markdown source versions of the field
     * values.
     */
    markdownTextFields: { [key: string]: string };

    /** Whether the review has been published. */
    public: boolean;

    /**
     * The contents of the raw text fields.
     *
     * This is set if the caller fetches or posts with
     * ``includeTextTypes=raw``. The keys in this object are the field names,
     * and the values are the raw versions of the field values.
     */
    rawTextFields: { [key: string]: string };

    /** Whether this review has the "Ship It!" state. */
    shipIt: boolean;

    /** The timestamp of the review. */
    timestamp: string;
}


/**
 * Review resource data returned by the server.
 *
 * Version Added:
 *     6.0
 */
interface ReviewResourceData {
    body_bottom: string;
    body_bottom_text_type: string;
    body_top: string;
    body_top_text_type: string;
    force_text_type: string;
    html_text_fields: { [key: string]: string };
    include_text_types: string;
    markdown_text_fields: { [key: string]: string };
    public: boolean;
    raw_text_fields: { [key: string]: string };
    ship_it: boolean;
    timestamp: string;
}


/**
 * Options for the create diff comment operation.
 *
 * Version Added:
 *     6.0
 */
interface CreateDiffCommentOptions {
    /**
     * The ID of the base filediff.
     *
     * This is the base diff when commenting on a cumulative diff. This is
     * mutually exclusive with ``interFileDiffID``.
     */
    baseFileDiffID: number;

    /** The line number of the start of the comment. */
    beginLineNum: number;

    /** The line number of the end of the comment. */
    endLineNum: number;

    /** The ID of the FileDiff that this comment is for. */
    fileDiffID: number;

    /** The ID for the new model (in the case of existing comments. */
    id: number;

    /**
     * The ID of the FileDiff that represents the "new" side of an interdiff.
     *
     * If specified, the ``fileDiffID`` represents the "old" side. This option
     * is mutually exclusive with ``baseFileDiffID``.
     */
    interFileDiffID: number;
}


/**
 * A review.
 *
 * This corresponds to a top-level review. Replies are encapsulated in
 * ReviewReply.
 */
@spina({
    prototypeAttrs: [
        'attrToJsonMap',
        'deserializedAttrs',
        'rspNamespace',
        'serializedAttrs',
        'serializers',
        'supportsExtraData',
    ],
})
export class Review<
    TAttributes extends ReviewAttrs = ReviewAttrs
> extends BaseResource<TAttributes> {
    /**
     * Return default values for the model attributes.
     *
     * Returns:
     *     ReviewAttrs:
     *     The attribute defaults.
     */
    defaults(): TAttributes {
        return _.defaults({
            'authorName': null,
            'bodyBottom': null,
            'bodyBottomRichText': false,
            'bodyTop': null,
            'bodyTopRichText': false,
            'draftReply': null,
            'forceTextType': null,
            'htmlTextFields': {},
            'includeTextTypes': null,
            'markdownTextFields': {},
            'public': false,
            'rawTextFields': {},
            'shipIt': false,
            'timestamp': null,
        }, super.defaults());
    }

    static rspNamespace = 'review';

    static attrToJsonMap = {
        bodyBottom: 'body_bottom',
        bodyBottomRichText: 'body_bottom_text_type',
        bodyTop: 'body_top',
        bodyTopRichText: 'body_top_text_type',
        forceTextType: 'force_text_type',
        includeTextTypes: 'include_text_types',
        shipIt: 'ship_it',
    };

    static serializedAttrs = [
        'forceTextType',
        'includeTextTypes',
        'shipIt',
        'bodyTop',
        'bodyTopRichText',
        'bodyBottom',
        'bodyBottomRichText',
        'public',
    ];

    static deserializedAttrs = [
        'shipIt',
        'bodyTop',
        'bodyBottom',
        'public',
        'timestamp',
    ];

    static serializers = {
        'bodyBottomRichText': JSONSerializers.textType,
        'bodyTopRichText': JSONSerializers.textType,
        'forceTextType': JSONSerializers.onlyIfValue,
        'includeTextTypes': JSONSerializers.onlyIfValue,
        'public': value => { return value ? 1 : undefined; },
    };

    static supportsExtraData = true;

    /**
     * Parse the response from the server.
     *
     * Args:
     *    rsp (object):
     *        The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData(
        rsp: ReviewResourceData,
    ): Partial<TAttributes> {
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = super.parseResourceData(rsp) as Partial<TAttributes>;

        data.bodyTopRichText =
            (rawTextFields.body_top_text_type === 'markdown');
        data.bodyBottomRichText =
            (rawTextFields.body_bottom_text_type === 'markdown');

        if (rsp.raw_text_fields) {
            data.rawTextFields = {
                bodyBottom: rsp.raw_text_fields.body_bottom,
                bodyTop: rsp.raw_text_fields.body_top,
            };
        }

        if (rsp.markdown_text_fields) {
            data.markdownTextFields = {
                bodyBottom: rsp.markdown_text_fields.body_bottom,
                bodyTop: rsp.markdown_text_fields.body_top,
            };
        }

        if (rsp.html_text_fields) {
            data.htmlTextFields = {
                bodyBottom: rsp.html_text_fields.body_bottom,
                bodyTop: rsp.html_text_fields.body_top,
            };
        }

        return data;
    }

    /**
     * Create a new diff comment for this review.
     *
     * Args:
     *     options (object):
     *         Options for creating the review.
     *
     * Option Args:
     *     id (number):
     *         The ID for the new model (in the case of existing comments).
     *
     *     fileDiffID (number):
     *         The ID of the FileDiff that this comment is for.
     *
     *     interFileDiffID (number):
     *         The ID of the FileDiff that represents the "new" side of an
     *         interdiff. If this is specified, the ``fileDiffID`` argument
     *         represents the "old" side.
     *
     *         This option is mutually exclusive with ``baseFileDiffID``.
     *
     *     beginLineNum (number):
     *         The line number of the start of the comment.
     *
     *     endLineNum (number):
     *         The line number of the end of the comment.
     *
     *     baseFileDiffID (number):
     *         The ID of the base FileDiff in the cumulative diff that the
     *         comment is to be made upon.
     *
     *         This option is mutually exclusive with ``interFileDiffID``.
     *
     * Returns:
     *     RB.DiffComment:
     *     The new comment object.
     */
    createDiffComment(
        options: CreateDiffCommentOptions,
    ): RB.DiffComment {
        if (!!options.interFileDiffID && !!options.baseFileDiffID) {
            console.error(
                'Options `interFileDiffID` and `baseFileDiffID` for ' +
                'RB.Review.createDiffComment() are mutually exclusive.');

            return null;
        }

        return new RB.DiffComment(_.defaults({parentObject: this}, options));
    }

    /**
     * Create a new screenshot comment for this review.
     *
     * Args:
     *     id (number):
     *         The ID for the new model (in the case of existing comments).
     *
     *     screenshotID (number):
     *         The ID of the Screenshot that this comment is for.
     *
     *     x (number):
     *         The X coordinate of the pixel for the upper left of the comment
     *         region.
     *
     *     y (number):
     *         The Y coordinate of the pixel for the upper left of the comment
     *         region.
     *
     *     width (number):
     *         The width of the comment region, in pixels.
     *
     *     height (number):
     *         The height of the comment region, in pixels.
     *
     * Returns:
     *     RB.ScreenshotComment:
     *     The new comment object.
     */
    createScreenshotComment(
        id: number,
        screenshotID: number,
        x: number,
        y: number,
        width: number,
        height: number,
    ): RB.ScreenshotComment {
        return new RB.ScreenshotComment({
            height: height,
            id: id,
            parentObject: this,
            screenshotID: screenshotID,
            width: width,
            x: x,
            y: y,
        });
    }

    /**
     * Create a new file attachment comment for this review.
     *
     * Args:
     *     id (number):
     *         The ID for the new model (in the case of existing comments).
     *
     *     fileAttachmentID (number):
     *         The ID of the FileAttachment that this comment is for.
     *
     *     diffAgainstFileAttachmentID (number):
     *         The ID of the FileAttachment that the ``fileAttachmentID`` is
     *         diffed against, if the comment is for a file diff.
     *
     * Returns:
     *     RB.FileAttachmentComment:
     *     The new comment object.
     */
    createFileAttachmentComment(
        id: number,
        fileAttachmentID: number,
        diffAgainstFileAttachmentID: number,
    ): RB.FileAttachmentComment {
        return new RB.FileAttachmentComment({
            diffAgainstFileAttachmentID: diffAgainstFileAttachmentID,
            fileAttachmentID: fileAttachmentID,
            id: id,
            parentObject: this,
        });
    }

    /**
     * Create a new general comment for this review.
     *
     * Args:
     *     id (number):
     *         The ID for the new model (in the case of existing comments).
     *
     *     issueOpened (boolean):
     *         Whether this comment should have an open issue.
     *
     * Returns:
     *     RB.GeneralComment:
     *     The new comment object.
     */
    createGeneralComment(
        id: number,
        issueOpened: boolean,
    ): RB.GeneralComment {
        return new RB.GeneralComment({
            id: id,
            issueOpened: issueOpened,
            parentObject: this,
        });
    }

    /**
     * Create a new reply.
     *
     * If an existing draft reply exists, return that. Otherwise create a draft
     * reply.
     *
     * Returns:
     *     RB.ReviewReply:
     *     The new reply object.
     */
    createReply(): ReviewReply {
        let draftReply = this.get('draftReply');

        if (draftReply === null) {
            draftReply = new ReviewReply({
                parentObject: this,
            });
            this.set('draftReply', draftReply);

            draftReply.once('published', () => {
                const reviewRequest = this.get('parentObject');
                reviewRequest.markUpdated(draftReply.get('timestamp'));
                this.set('draftReply', null);
            });
        }

        return draftReply;
    }
}
