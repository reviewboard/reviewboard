/**
 * Provides review capabilities for screenshots.
 */
RB.ScreenshotReviewable = RB.AbstractReviewable.extend({
    defaults: _.defaults({
        caption: '',
        imageURL: '',
        screenshotID: null,
    }, RB.AbstractReviewable.prototype.defaults),

    commentBlockModel: RB.ScreenshotCommentBlock,
    defaultCommentBlockFields: ['screenshotID'],

    /**
     * Load a serialized comment and add comment blocks for it.
     *
     * Args:
     *     serializedCommentBlock (object):
     *         The serialized data for the new comment block(s).
     */
    loadSerializedCommentBlock(serializedCommentBlock) {
        this.createCommentBlock({
            screenshotID: this.get('screenshotID'),
            x: serializedCommentBlock[0].x,
            y: serializedCommentBlock[0].y,
            width: serializedCommentBlock[0].w,
            height: serializedCommentBlock[0].h,
            serializedComments: serializedCommentBlock,
        });
    },
});
