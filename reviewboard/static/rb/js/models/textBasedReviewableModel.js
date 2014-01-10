/*
 * Provides generic review capabilities for text-based file attachments.
 */
RB.TextBasedReviewable = RB.FileAttachmentReviewable.extend({
    defaults: _.defaults({
        viewMode: 'source',
        hasRenderedView: false
    }, RB.FileAttachmentReviewable.prototype.defaults),

    commentBlockModel: RB.TextCommentBlock,

    defaultCommentBlockFields: [
        'viewMode'
    ].concat(RB.FileAttachmentReviewable.prototype.defaultCommentBlockFields)
});
