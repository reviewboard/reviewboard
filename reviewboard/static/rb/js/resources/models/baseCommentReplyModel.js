/*
 * The base class for a reply to a type of comment.
 *
 * This handles all the serialization/deserialization for comment replies.
 * Subclasses are expected to provide the rspNamespace, but don't need to
 * provide any additional functionality.
 */
RB.BaseCommentReply = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            /*
             * The text format type to request for text in all responses.
             */
            forceTextType: null,

            /*
             * A string containing a comma-separated list of text types to include
             * in the payload.
             */
            includeTextTypes: null,

            /*
             * Raw text fields, if the caller fetches or posts with
             * include-text-types=raw.
             */
            rawTextFields: {},

            /* The ID of the comment being replied to. */
            replyToID: null,

            /* Whether the reply text is saved in rich-text (Markdown) format. */
            richText: false,

            /* The text entered for the comment. */
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

    /*
     * Destroys the comment reply if and only if the text is empty.
     *
     * This works just like destroy(), and will in fact call destroy()
     * with all provided arguments, but only if there's some actual
     * text in the reply.
     */
    destroyIfEmpty: function(options, context) {
        if (!this.get('text')) {
            this.destroy(options, context);
        }
    },

    /*
     * Deserializes comment reply data from an API payload.
     *
     * This must be overloaded by subclasses, and the parent version called.
     */
    parseResourceData: function(rsp) {
        var rawTextFields = rsp.raw_text_fields || rsp,
            data = RB.BaseResource.prototype.parseResourceData.call(this, rsp);

        data.rawTextFields = rsp.raw_text_fields || {};
        data.richText = (rawTextFields.text_type === 'markdown');

        return data;
    },

    /*
     * Performs validation on the attributes of the model.
     *
     * By default, this validates that there's a parentObject set. It
     * can be overridden to provide additional validation, but the parent
     * function must be called.
     */
    validate: function(attrs) {
        if (_.has(attrs, 'parentObject') && !attrs.parentObject) {
            return RB.BaseResource.strings.UNSET_PARENT_OBJECT;
        }
    }
});
