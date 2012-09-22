/*
 * Provides review capabilities for screenshots.
 */
RB.ScreenshotReviewable = RB.AbstractReviewable.extend({
    defaults: _.defaults({
        caption: '',
        imageURL: '',
        screenshotID: null
    }, RB.AbstractReviewable.prototype.defaults),

    commentBlockModel: RB.ScreenshotCommentBlock,

    /*
     * Adds comment blocks for the serialized comments passed to the
     * reviewable.
     */
    addCommentBlocks: function(serializedComments) {
        this.commentBlocks.add({
            screenshotID: this.get('screenshotID'),
            x: serializedComments[0].x,
            y: serializedComments[0].y,
            width: serializedComments[0].w,
            height: serializedComments[0].h,
            serializedComments: serializedComments || []
        });
    }
});
