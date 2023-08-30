/**
 * A review reply.
 */

import { spina } from '@beanbag/spina';

import * as JSONSerializers from '../utils/serializers';
import { BaseResource, BaseResourceAttrs} from './baseResourceModel';
import { DraftResourceModelMixin } from './draftResourceModelMixin';
import { Review } from './reviewModel';


/**
 * Attributes for the ReviewReply model.
 *
 * Version Added:
 *     6.0
 */
interface ReviewReplyAttrs extends BaseResourceAttrs {
    /** The reply to the original review's ``bodyBottom``. */
    bodyBottom: string;

    /** Whether the ``bodyBottom`` field should be rendered as Markdown. */
    bodyBottomRichText: boolean;

    /** The reply to the original review's ``bodyTop``. */
    bodyTop: string;

    /** Whether the ``bodyTop`` field should be rendered as Markdown. */
    bodyTopRichText: boolean;

    /** The text type to request for text in all responses. */
    forceTextType: string;

    /** A comma-separated list of text types to include in responses. */
    includeTextTypes: string;

    /** Whether this reply has been published. */
    public: boolean;

    /**
     * The contents of the raw text fields.
     *
     * This is set if ``forceTextType`` is used, and the caller fetches or
     * posts with ``includeTextTypes=raw``. The keys in this object are the
     * field names, and the values ar the raw versions of those attributes.
     */
    rawTextFields: { [key: string]: string };

    /** The review being replied to. */
    review: Review;

    /** The timestamp of the reply. */
    timestamp: string;
}


/**
 * ReviewReply resource data returned by the server.
 *
 * Version Added:
 *     6.0
 */
interface ReviewReplyResourceData {
    body_bottom: string;
    body_bottom_text_type: string;
    body_top: string;
    body_top_text_type: string;
    force_text_type: string;
    include_text_types: string;
    raw_text_fields: { [key: string]: string };
}


/**
 * Options for the publish operation.
 *
 * Version Added:
 *     6.0
 */
interface ReviewReplyPublishOptions extends Backbone.PersistenceOptions {
    /** Whether to suppress e-mail notifications. */
    trivial?: boolean;
}


/**
 * A review reply.
 *
 * Encapsulates replies to a top-level review.
 */
@spina({
    mixins: [DraftResourceModelMixin],
    prototypeAttrs: [
        'COMMENT_LINK_NAMES',
        'attrToJsonMap',
        'deserializedAttrs',
        'extraQueryArgs',
        'listKey',
        'rspNamespace',
        'serializedAttrs',
        'serializers',
    ],
})
export class ReviewReply extends BaseResource<ReviewReplyAttrs> {
    /**
     * Return default values for the model attributes.
     *
     * Returns:
     *     ReviewReplyAttrs:
     *     The default attributes.
     */
    defaults(): ReviewReplyAttrs {
        return _.defaults({
            bodyBottom: null,
            bodyBottomRichText: false,
            bodyTop: null,
            bodyTopRichText: false,
            forceTextType: null,
            includeTextTypes: null,
            'public': false,
            rawTextFields: {},
            review: null,
            timestamp: null,
        }, super.defaults());
    }

    static rspNamespace = 'reply';
    static listKey = 'replies';

    static extraQueryArgs = {
        'force-text-type': 'html',
        'include-text-types': 'raw',
    };

    static attrToJsonMap = {
        bodyBottom: 'body_bottom',
        bodyBottomRichText: 'body_bottom_text_type',
        bodyTop: 'body_top',
        bodyTopRichText: 'body_top_text_type',
        forceTextType: 'force_text_type',
        includeTextTypes: 'include_text_types',
    };

    static serializedAttrs = [
        'bodyBottom',
        'bodyBottomRichText',
        'bodyTop',
        'bodyTopRichText',
        'forceTextType',
        'includeTextTypes',
        'public',
    ];

    static deserializedAttrs = [
        'bodyBottom',
        'bodyTop',
        'public',
        'timestamp',
    ];

    static serializers = {
        bodyBottomRichText: JSONSerializers.textType,
        bodyTopRichText: JSONSerializers.textType,
        forceTextType: JSONSerializers.onlyIfValue,
        includeTextTypes: JSONSerializers.onlyIfValue,
        'public': value => { return value ? true : undefined; },
    };

    static COMMENT_LINK_NAMES = [
        'diff_comments',
        'file_attachment_comments',
        'general_comments',
        'screenshot_comments',
    ];

    /**
     * Parse the response from the server.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     The attribute values to set on the model.
     */
    parseResourceData(
        rsp: ReviewReplyResourceData,
    ): Partial<ReviewReplyAttrs> {
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = super.parseResourceData(rsp) as ReviewReplyAttrs;

        data.bodyTopRichText =
            (rawTextFields.body_top_text_type === 'markdown');
        data.bodyBottomRichText =
            (rawTextFields.body_bottom_text_type === 'markdown');
        data.rawTextFields = rsp.raw_text_fields || {};

        return data;
    }

    /**
     * Publish the reply.
     *
     * Before publishing, the "publishing" event will be triggered.
     * After successfully publishing, "published" will be triggered.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
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
    async publish(
        options: ReviewReplyPublishOptions = {},
        context: unknown = undefined,
    ): Promise<void> {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ReviewReply.publish was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');

            return RB.promiseToCallbacks(options, context, newOptions =>
                this.publish(newOptions));
        }

        this.trigger('publishing');

        await this.ready();

        this.set('public', true);

        try {
            await this.save({
                data: {
                    'public': 1,
                    trivial: options.trivial ? 1 : 0,
                },
            });
        } catch (err) {
            this.trigger('publishError', err.message);
            throw err;
        }

        this.trigger('published');
    }

    /**
     * Discard the reply if it's empty.
     *
     * If the reply doesn't have any remaining comments on the server, then
     * this will discard the reply.
     *
     * Version Changed:
     *     5.0:
     *     Changed to deprecate options and return a promise.
     *
     * Args:
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete. The
     *     resolution value will be true if discarded, false otherwise.
     */
    async discardIfEmpty(
        options: Backbone.PersistenceOptions = {},
        context: unknown = undefined,
    ): Promise<boolean> {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ReviewReply.discardIfEmpty was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');

            return RB.promiseToCallbacks(options, context, newOptions =>
                this.discardIfEmpty(newOptions));
        }

        await this.ready();

        if (this.isNew() || this.get('bodyTop') || this.get('bodyBottom')) {
            return false;
        } else {
            return this._checkCommentsLink(0);
        }
    }

    /**
     * Check if there are comments, given the comment type.
     *
     * This is part of the discardIfEmpty logic.
     *
     * If there are comments, we'll give up and call options.success(false).
     *
     * If there are no comments, we'll move on to the next comment type. If
     * we're done, the reply is discarded, and options.success(true) is called.
     *
     * Args:
     *     linkNamesIndex (number):
     *         An index into the ``COMMENT_LINK_NAMES`` Array.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete. The
     *     resolution value will be true if discarded, false otherwise.
     */
    _checkCommentsLink(
        linkNameIndex: number,
    ): Promise<boolean> {
        return new Promise((resolve, reject) => {
            const linkName = ReviewReply.COMMENT_LINK_NAMES[linkNameIndex];
            const url = this.get('links')[linkName].href;

            RB.apiCall({
                error: (model, xhr, options) => reject(
                    new BackboneError(model, xhr, options)),
                success: rsp => {
                    if (rsp[linkName].length > 0) {
                        resolve(false);
                    } else if (linkNameIndex <
                               ReviewReply.COMMENT_LINK_NAMES.length - 1) {
                        resolve(this._checkCommentsLink(linkNameIndex + 1));
                    } else {
                        resolve(this.destroy().then(() => true));
                    }
                },
                type: 'GET',
                url: url,
            });
        });
    }
}
