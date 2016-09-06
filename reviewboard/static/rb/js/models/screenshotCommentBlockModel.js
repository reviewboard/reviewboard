/*
 * Represents the comments on a region of a screenshot.
 *
 * ScreenshotCommentBlock deals with creating and representing comments
 * that exist in a specific region of a screenshot.
 */
RB.ScreenshotCommentBlock = RB.AbstractCommentBlock.extend({
    defaults: _.defaults({
        screenshotID: null,
        x: null,
        y: null,
        width: null,
        height: null
    }, RB.AbstractCommentBlock.prototype.defaults),

    /*
     * Return whether the bounds of this region can be updated.
     *
     * If there are any existing published comments on this region, it
     * cannot be updated.
     *
     * Returns:
     *     boolean:
     *     A value indicating whether new bounds can be set for this region.
     */
    canUpdateBounds: function() {
        return false;
    },

    /*
     * Creates a ScreenshotComment for the given comment ID and this block's
     * region.
     */
    createComment: function(id) {
        return this.get('review').createScreenshotComment(
            id, this.get('screenshotID'), this.get('x'), this.get('y'),
            this.get('width'), this.get('height'));
    }
});
