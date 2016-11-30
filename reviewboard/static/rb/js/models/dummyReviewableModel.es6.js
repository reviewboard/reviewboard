/**
 * Generic review capabilities for file types which cannot be displayed.
 */
RB.DummyReviewable = RB.FileAttachmentReviewable.extend({
    commentBlockModel: RB.AbstractCommentBlock,
});
