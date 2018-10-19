/**
 * Represents the comments on an element in a text-based file attachment.
 *
 * TextCommentBlock deals with creating and representing comments
 * that exist on a specific element of some content.
 *
 * Model Attributes:
 *     viewMode (string):
 *         The mode of text that the comment is made upon. This is one of:
 *
 *         ``'source'``:
 *             The raw contents of the file.
 *
 *         ``'rendered'``:
 *             The rendered contents of the file, such as for Markdown, etc.
 *
 *     beginLineNum (number):
 *         The first line number in the file that this comment is on.
 *
 *     endLineNUm (number):
 *         The last line number in the file that this comment is on.
 *
 *     $beginRow (jQuery):
 *         The first row in the diffviewer that this comment is on.
 *
 *     $endRow (jQuery):
 *         The last row in the diffviewer that this comment is on.
 *
 * See Also:
 *     :js:class:`RB.FileAttachmentCommentBlock`:
 *         For the attributes defined by the base model.
 *
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For the attributes defined on all comment block.
 */
RB.TextCommentBlock = RB.FileAttachmentCommentBlock.extend({
    defaults: _.defaults({
        beginLineNum: null,
        endLineNum: null,
        viewMode: false,
        $beginRow: null,
        $endRow: null,
    }, RB.FileAttachmentCommentBlock.prototype.defaults),

    serializedFields: ['beginLineNum', 'endLineNum', 'viewMode'],

    /**
     * Parse the incoming attributes for the comment block.
     *
     * The fields are stored server-side as strings, so we need to convert
     * them back to integers where appropriate.
     *
     * Args:
     *     fields (object):
     *         The attributes for the comment, as returned by the server.
     *
     * Returns:
     *     object:
     *     The parsed data.
     */
    parse(fields) {
        fields.beginLineNum = parseInt(fields.beginLineNum, 10);
        fields.endLineNum = parseInt(fields.endLineNum, 10);

        return fields;
    },
});
