/**
 * Represents the comments on a region of a screenshot.
 *
 * ScreenshotCommentBlock deals with creating and representing comments
 * that exist in a specific region of a screenshot.
 *
 * Model Attributes:
 *     screenshotID (number):
 *         The ID of the screenshot being commented upon.
 *
 *     x (number):
 *         The X position of the region being commented upon.
 *
 *     y (number):
 *         The Y position of the region being commented upon.
 *
 *     width (number):
 *         The width of the region being commented upon.
 *
 *     height (number):
 *         The height of the region being commented upon.
 *
 * See Also:
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For attributes defined on the base model.
 */
RB.ScreenshotCommentBlock = RB.AbstractCommentBlock.extend({
    defaults: _.defaults({
        screenshotID: null,
        x: null,
        y: null,
        width: null,
        height: null,
    }, RB.AbstractCommentBlock.prototype.defaults),

    /**
     * Return whether the bounds of this region can be updated.
     *
     * If there are any existing published comments on this region, it
     * cannot be updated.
     *
     * Returns:
     *     boolean:
     *     A value indicating whether new bounds can be set for this region.
     */
    canUpdateBounds() {
        return false;
    },

    /**
     * Creates a ScreenshotComment for the given comment ID.
     *
     * Args:
     *     id (number):
     *         The ID of the comment to instantiate the model for.
     *
     * Returns:
     *     RB.ScreenshotComment:
     *     The new comment model.
     */
    createComment(id) {
        return this.get('review').createScreenshotComment(
            id, this.get('screenshotID'), this.get('x'), this.get('y'),
            this.get('width'), this.get('height'));
    },
});
