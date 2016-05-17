/**
 * A reply to a diff comment made on a review.
 *
 * When created, this must take a parentObject attribute that points to a
 * Review object.
 */
RB.DiffCommentReply = RB.BaseCommentReply.extend({
    rspNamespace: 'diff_comment'
});
