/*
 * Represents the comments on an element in a text-based file attachment.
 *
 * TextCommentBlock deals with creating and representing comments
 * that exist on a specific element of some content.
 */
RB.TextCommentBlock = RB.FileAttachmentCommentBlock.extend({
    defaults: _.defaults({
        beginLineNum: null,
        endLineNum: null,
        viewMode: false,
        $beginRow: null,
        $endRow: null
    }, RB.FileAttachmentCommentBlock.prototype.defaults),

    serializedFields: ['beginLineNum', 'endLineNum', 'viewMode'],

    /*
     * Parses the incoming attributes for the comment block.
     *
     * The fields are stored server-side as strings, so we need to convert
     * them back to integers where appropriate.
     */
    parse: function(fields) {
        fields.beginLineNum = parseInt(fields.beginLineNum, 10);
        fields.endLineNum = parseInt(fields.endLineNum, 10);

        return fields;
    }
});
