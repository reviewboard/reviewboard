/*
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
        $endRow: null
    }, RB.AbstractCommentBlock.prototype.defaults),

    /*
     * Returns the number of lines this comment block spans.
     */
    getNumLines: function() {
        return this.get('endLineNum') + this.get('beginLineNum') + 1;
    },

    /*
     * Creates a DiffComment for the given comment ID and this block's
     * line range.
     */
    createComment: function(id) {
        return this.get('review').createDiffComment(
            id,
            this.get('fileDiffID'),
            this.get('interFileDiffID'),
            this.get('beginLineNum'),
            this.get('endLineNum'));
    }
});
