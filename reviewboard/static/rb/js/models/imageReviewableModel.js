/*
 * Provides review capabilities for image file attachments.
 */
RB.ImageReviewable = RB.FileAttachmentReviewable.extend({
    defaults: _.defaults({
        imageURL: ''
    }, RB.FileAttachmentReviewable.prototype.defaults),

    commentBlockModel: RB.RegionCommentBlock
});

