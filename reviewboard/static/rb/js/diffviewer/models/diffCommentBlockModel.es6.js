/**
 * Represents the comments on a region of a diff.
 *
 * DiffCommentBlock deals with creating and representing comments that exist
 * in a specific line range of a diff.
 */
RB.DiffCommentBlock = RB.AbstractCommentBlock.extend({
    defaults: _.defaults({
        fileDiffID: null,
        interFileDiffID: null,
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
    getNumLines: function() {
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
    createComment: function(id) {
        return this.get('review').createDiffComment(
            id,
            this.get('fileDiffID'),
            this.get('interFileDiffID'),
            this.get('beginLineNum'),
            this.get('endLineNum'));
    },
});
