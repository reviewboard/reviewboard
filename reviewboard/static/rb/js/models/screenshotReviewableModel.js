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
    defaultCommentBlockFields: ['screenshotID'],

    /*
     * Adds comment blocks for the serialized comment block passed to the
     * reviewable.
     */
    loadSerializedCommentBlock: function(serializedCommentBlock) {
        this.createCommentBlock({
            screenshotID: this.get('screenshotID'),
            x: serializedCommentBlock[0].x,
            y: serializedCommentBlock[0].y,
            width: serializedCommentBlock[0].w,
            height: serializedCommentBlock[0].h,
            serializedComments: serializedCommentBlock
        });
    }
});
