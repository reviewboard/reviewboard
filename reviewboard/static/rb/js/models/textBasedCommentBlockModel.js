/*
 * Represents the comments on an element in a text-based file attachment.
 *
 * TextCommentBlock deals with creating and representing comments
 * that exist on a specific element of some content.
 */
RB.TextCommentBlock = RB.FileAttachmentCommentBlock.extend({
    defaults: _.defaults({
        child_id: null
    }, RB.FileAttachmentCommentBlock.prototype.defaults),

    serializedFields: ['child_id'],

    /*
     * Parses the incoming attributes for the comment block.
     *
     * The fields are stored server-side as strings, so we need to convert
     * them back to integers where appropriate.
     */
    parse: function(fields) {
        fields.child_id = parseInt(fields.child_id, 10) || undefined;
        return fields;
    }
});
