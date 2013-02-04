/*
 * The base class for a reply to a type of comment.
 *
 * This handles all the serialization/deserialization for comment replies.
 * Subclasses are expected to provide the rspNamespace, but don't need to
 * provide any additional functionality.
 */
RB.BaseCommentReply = RB.BaseResource.extend({
    defaults: _.defaults({
        /* The ID of the comment being replied to. */
        replyToID: null,

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
            text: this.get('text')
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
    parse: function(rsp) {
        var result = RB.BaseResource.prototype.parse.call(this, rsp),
            rspData = rsp[this.rspNamespace];

        result.text = rspData.text;

        return result;
    },

    /*
     * Performs validation on the attributes of the model.
     *
     * By default, this validates that there's a parentObject set. It
     * can be overridden to provide additional validation, but the parent
     * function must be called.
     */
    validate: function(attrs, options) {
        if (_.has(attrs, 'parentObject') && !attrs.parentObject) {
            return RB.BaseResource.strings.UNSET_PARENT_OBJECT;
        }
    }
});
