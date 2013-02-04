/*
 * A reply to a file attachment comment made on a review.
 *
 * When created, this must take a parentObject attribute that points to a
 * Review object.
 */
RB.FileAttachmentCommentReply = RB.BaseCommentReply.extend({
    rspNamespace: 'file_attachment_comment'
});
