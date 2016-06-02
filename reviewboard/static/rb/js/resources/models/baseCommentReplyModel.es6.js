/**
 * The base class for a reply to a type of comment.
 *
 * This handles all the serialization/deserialization for comment replies.
 * Subclasses are expected to provide the rspNamespace, but don't need to
 * provide any additional functionality.
 *
 * Model Attributes:
 *     forceTextType (string):
 *         The text format type to request for text in all responses.
 *
 *     includeTextTypes (string):
 *         A comma-separated list of text types to include in the payload when
 *         syncing the model.
 *
 *     rawTextFields (object):
 *         The contents of the raw text fields, if forceTextType is used and
 *         the caller fetches or posts with includeTextTypes=raw. The keys in this
 *         object are the field names, and the values are the raw versions of
 *         those attributes.
 *
 *     replyToID (number):
 *         The ID of the comment that this reply is replying to.
 *
 *     richText (boolean):
 *         Whether the reply text is saved in rich text (Markdown) format.
 *
 *     text (string):
 *         The text of the reply.
 */
RB.BaseCommentReply = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            forceTextType: null,
            includeTextTypes: null,
            rawTextFields: {},
            replyToID: null,
            richText: false,
            text: ''
        }, RB.BaseResource.prototype.defaults());
    },

    attrToJsonMap: {
        forceTextType: 'force_text_type',
        includeTextTypes: 'include_text_types',
        replyToID: 'reply_to_id',
        richText: 'text_type'
    },

    serializedAttrs: [
        'forceTextType',
        'includeTextTypes',
        'replyToID',
        'richText',
        'text'
    ],

    deserializedAttrs: [
        'text'
    ],

    serializers: {
        forceTextType: RB.JSONSerializers.onlyIfValue,
        includeTextTypes: RB.JSONSerializers.onlyIfValue,
        replyToID: RB.JSONSerializers.onlyIfUnloaded,
        richText: RB.JSONSerializers.textType
    },

    /**
     * Destroy the comment reply if and only if the text is empty.
     *
     * This works just like destroy(), and will in fact call destroy()
     * with all provided arguments, but only if there's some actual
     * text in the reply.
     */
    destroyIfEmpty() {
        if (!this.get('text')) {
            this.destroy.apply(this, arguments);
        }
    },

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
    parseResourceData(rsp) {
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = RB.BaseResource.prototype.parseResourceData.call(
            this, rsp);

        data.rawTextFields = rsp.raw_text_fields || {};
        data.richText = (rawTextFields.text_type === 'markdown');

        return data;
    },

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
    validate(attrs) {
        if (_.has(attrs, 'parentObject') && !attrs.parentObject) {
            return RB.BaseResource.strings.UNSET_PARENT_OBJECT;
        }
    }
});
