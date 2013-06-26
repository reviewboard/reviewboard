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
     * Creates a ScreenshotComment for the given comment ID and this block's
     * region.
     */
    createComment: function(id) {
        return this.get('review').createScreenshotComment(
            id, this.get('screenshotID'), this.get('x'), this.get('y'),
            this.get('width'), this.get('height'));
    }
});
