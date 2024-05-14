/**
 * The base class for a reply to a type of comment.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import * as JSONSerializers from '../utils/serializers';
import {
    type BaseResourceAttrs,
    type BaseResourceResourceData,
    type SerializerMap,
    BaseResource,
} from './baseResourceModel';


/**
 * Attributes for the BaseCommentReply model.
 *
 * Version Added:
 *     8.0
 */
export interface BaseCommentReplyAttrs extends BaseResourceAttrs {
    /** The text format type to request for text in all responses. */
    forceTextType: string | null;

    /**
     * A comma-separated list of text types.
     *
     * These will be requested from the server to include in the payload when
     * syncing the model.
     */
    includeTextTypes: string | null;

    /**
     * The contents of the raw text fields, if forceTextType is used and the
     * caller fetches or posts with includeTextTypes=raw. The keys in this
     * object are the field names, and the values are the raw versions of
     * those attributes.
     */
    rawTextFields: Record<string, string>;

    /** The ID of the comment that this reply is replying to. */
    replyToID: number | null;

    /** Whether the reply text is saved in rich text (Markdown) format. */
    richText: boolean;

    /** The text of the reply. */
    text: string;
}


/**
 * Resource data for the BaseCommentReply model.
 *
 * Version Added:
 *     8.0
 */
export interface BaseCommentReplyResourceData
extends BaseResourceResourceData {
    force_text_type: string | null;
    include_text_types: string | null;
    raw_text_fields: Record<string, string>;
    reply_to_id: number;
    text: string;
    text_type: string;
}


/**
 * The base class for a reply to a type of comment.
 *
 * This handles all the serialization/deserialization for comment replies.
 * Subclasses are expected to provide the rspNamespace, but don't need to
 * provide any additional functionality.
 */
@spina
export class BaseCommentReply<
    TDefaults extends BaseCommentReplyAttrs = BaseCommentReplyAttrs,
    TResourceData extends BaseCommentReplyResourceData =
        BaseCommentReplyResourceData,
> extends BaseResource<TDefaults, TResourceData> {
    static defaults(): Result<Partial<BaseCommentReplyAttrs>> {
        return {
            forceTextType: null,
            includeTextTypes: null,
            rawTextFields: {},
            replyToID: null,
            richText: false,
            text: '',
        };
    }

    static attrToJsonMap: Record<string, string> = {
        forceTextType: 'force_text_type',
        includeTextTypes: 'include_text_types',
        replyToID: 'reply_to_id',
        richText: 'text_type',
    };

    static serializedAttrs = [
        'forceTextType',
        'includeTextTypes',
        'replyToID',
        'richText',
        'text',
    ];

    static deserializedAttrs = [
        'text',
    ];

    static serializers: SerializerMap = {
        forceTextType: JSONSerializers.onlyIfValue,
        includeTextTypes: JSONSerializers.onlyIfValue,
        replyToID: JSONSerializers.onlyIfUnloaded,
        richText: JSONSerializers.textType,
    };

    /**
     * Destroy the comment reply if and only if the text is empty.
     *
     * This works just like destroy(), and will in fact call destroy()
     * with all provided arguments, but only if there's some actual
     * text in the reply.
     */
    destroyIfEmpty() {
        if (!this.get('text')) {
            this.destroy();
        }
    }

    /**
     * Deserialize comment reply data from an API payload.
     *
     * This must be overloaded by subclasses, and the parent version called.
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
        rsp: TResourceData,
    ): Partial<TDefaults> {
        const data = super.parseResourceData(rsp);

        data.rawTextFields = rsp.raw_text_fields || {};

        const rawTextFields = rsp.raw_text_fields || rsp;
        data.richText = (rawTextFields.text_type === 'markdown');

        return data;
    }

    /**
     * Validate the attributes of the model.
     *
     * By default, this validates that there's a parentObject set. It
     * can be overridden to provide additional validation, but the parent
     * function must be called.
     *
     * Args:
     *     attrs (object):
     *         Model attributes to validate.
     *
     * Returns:
     *     string:
     *     An error string, if appropriate.
     */
    validate(
        attrs: Partial<TDefaults>,
    ): string {
        if (_.has(attrs, 'parentObject') && !attrs.parentObject) {
            return BaseResource.strings.UNSET_PARENT_OBJECT;
        }
    }
}
