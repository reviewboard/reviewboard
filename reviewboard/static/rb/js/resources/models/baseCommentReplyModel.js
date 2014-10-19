/*
 * The base class for a reply to a type of comment.
 *
 * This handles all the serialization/deserialization for comment replies.
 * Subclasses are expected to provide the rspNamespace, but don't need to
 * provide any additional functionality.
 */
RB.BaseCommentReply = RB.BaseResource.extend({
    defaults: _.defaults({
        /*
         * The text format type to request for text in all responses.
         */
        forceTextType: null,

        /*
         * Whether responses from the server should return raw text
         * fields when forceTextType is used.
         */
        includeRawTextFields: false,

        /*
         * Raw text fields, if forceTextType is used and the caller
         * fetches or posts with include-raw-text-fields=1
         */
        rawTextFields: {},

        /* The ID of the comment being replied to. */
        replyToID: null,

        /* Whether the reply text is saved in rich-text (Markdown) format. */
        richText: false,

        /* The text entered for the comment. */
        text: ''
    }, RB.BaseResource.prototype.defaults),

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
     * Serializes the comment reply to a payload that can be sent to the server.
     *
     * This must be overloaded by subclasses, and the parent version called.
     */
    toJSON: function() {
        var data = {
            force_text_type: this.get('forceTextType') || undefined,
            include_raw_text_fields: this.get('includeRawTextFields') ||
                                     undefined,
            text: this.get('text'),
            text_type: this.get('richText') ? 'markdown' : 'plain'
        };

        if (!this.get('loaded')) {
            data.reply_to_id = this.get('replyToID');
        }

        return data;
    },

    /*
     * Deserializes comment reply data from an API payload.
     *
     * This must be overloaded by subclasses, and the parent version called.
     */
    parseResourceData: function(rsp) {
        var rawTextFields = rsp.raw_text_fields || rsp,
            data = {
                text: rsp.text,
                rawTextFields: rsp.raw_text_fields || {},
                richText: rawTextFields.text_type === 'markdown'
            };

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
