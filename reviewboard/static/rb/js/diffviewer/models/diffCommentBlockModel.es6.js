/**
 * Represents the comments on a region of a diff.
 *
 * DiffCommentBlock deals with creating and representing comments that exist
 * in a specific line range of a diff.
 *
 * Model Attributes:
 *     baseFileDiffID (number):
 *         The ID of the base FileDiff that this comment is on.
 *
 *         This attribute is mutually exclusive with interFileDiffID.
 *
 *     fileDiffID (number):
 *         The ID of the FileDiff that this comment is on.
 *
 *     interFileDiffID (number):
 *         The ID of the inter-FileDiff that this comment is on, if any.
 *
 *         This attribute is mutually exclusive with baseFileDiffID.
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
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For the attributes defined by the base model.
 */
RB.DiffCommentBlock = RB.AbstractCommentBlock.extend({
    defaults: _.defaults({
        fileDiffID: null,
        interFileDiffID: null,
        baseFileDiffID: null,
        beginLineNum: null,
        endLineNum: null,
        $beginRow: null,
        $endRow: null,
    }, RB.AbstractCommentBlock.prototype.defaults),

    /**
     * Return the number of lines this comment block spans.
     *
     * Returns:
     *     number:
     *     The number of lines spanned by this comment.
     */
    getNumLines() {
        return this.get('endLineNum') + this.get('beginLineNum') + 1;
    },

    /**
     * Create a DiffComment for the given comment ID.
     *
     * Args:
     *     id (number):
     *         The ID of the comment to instantiate the model for.
     *
     * Returns:
     *     RB.DiffComment:
     *     The new comment model.
     */
    createComment(id) {
        return this.get('review').createDiffComment({
            id: id,
            fileDiffID: this.get('fileDiffID'),
            interFileDiffID: this.get('interFileDiffID'),
            beginLineNum: this.get('beginLineNum'),
            endLineNum: this.get('endLineNum'),
            baseFileDiffID: this.get('baseFileDiffID'),
        });
    },
});
