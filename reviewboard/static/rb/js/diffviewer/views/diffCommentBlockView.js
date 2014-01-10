/*
 * Displays the comment flag for a comment in the diff viewer.
 *
 * The comment flag handles all interaction for creating/viewing
 * comments, and will update according to any comment state changes.
 */
RB.DiffCommentBlockView = RB.TextBasedCommentBlockView.extend({
    /*
     * Builds the name for the comment flag anchor.
     */
    buildAnchorName: function() {
        return 'file' + this.model.get('fileDiffID') + 'line' +
               this.model.get('beginLineNum');
    }
});
