/**
 * Displays the comment flag for a comment in the diff viewer.
 *
 * The comment flag handles all interaction for creating/viewing
 * comments, and will update according to any comment state changes.
 */
RB.DiffCommentBlockView = RB.TextBasedCommentBlockView.extend({
    /**
     * Return the name for the comment flag anchor.
     *
     * Returns:
     *     The name to use for the anchor element.
     */
    buildAnchorName() {
        const fileDiffID = this.model.get('fileDiffID');
        const beginLineNum = this.model.get('beginLineNum');

        return `file${fileDiffID}line${beginLineNum}`;
    },
});
