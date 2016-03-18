/**
 * A reply to a general comment made on a review.
 *
 * When created, this must take a parentObject attribute that points to a
 * Review object.
 */
RB.GeneralCommentReply = RB.BaseCommentReply.extend({
    rspNamespace: 'general_comment'
});
