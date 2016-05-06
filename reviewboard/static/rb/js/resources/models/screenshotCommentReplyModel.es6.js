/**
 * A reply to a screenshot comment made on a review.
 *
 * When created, this must take a parentObject attribute that points to a
 * Review object.
 */
RB.ScreenshotCommentReply = RB.BaseCommentReply.extend({
    rspNamespace: 'screenshot_comment'
});
