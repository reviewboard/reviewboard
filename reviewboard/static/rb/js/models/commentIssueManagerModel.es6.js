/**
 * CommentIssueManager takes care of setting the state of a particular
 * comment issue, and also takes care of notifying callbacks whenever
 * the state is successfully changed.
 */
RB.CommentIssueManager = Backbone.Model.extend({
    defaults: {
        reviewRequest: null,
    },

    /**
     * Initialize the model.
     */
    initialize() {
        this._comments = {};
    },

    /**
     * Set the state for a comment.
     *
     * Args:
     *     reviewID (number):
     *         The ID of the review the comment belongs to.
     *
     *     commentID (number):
     *         The ID of the comment.
     *
     *     commentType (string):
     *         The type of the comment.
     *
     *     state (string):
     *          The new state for the comment's issue. This will be one of
     *          ``open``, ``resolved``, ``dropped``, or ``verify``.
     */
    setCommentState(reviewID, commentID, commentType, state) {
        const comment = this.getComment(reviewID, commentID, commentType);
        this._requestState(comment, state);
    },

    /**
     * Retrieve the model for a given comment.
     *
     * This will either generate the appropriate comment object based on
     * ``commentType``, or grab the comment from a cache if it's been generated
     * before.
     *
     * Args:
     *     reviewID (number):
     *         The ID of the review the comment belongs to.
     *
     *     commentID (number):
     *         The ID of the comment.
     *
     *     commentType (string):
     *         The type of the comment.
     *
     * Returns:
     *     RB.BaseComment:
     *     The comment model.
     */
    getComment(reviewID, commentID, commentType) {
        if (!this._comments[commentID]) {
            const reviewRequest = this.get('reviewRequest');
            let comment = null;

            switch (commentType) {
                case 'diff_comments':
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createDiffComment({id: commentID});
                    break;

                case 'screenshot_comments':
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createScreenshotComment(commentID);
                    break;

                case 'file_attachment_comments':
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createFileAttachmentComment(commentID);
                    break;

                case 'general_comments':
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createGeneralComment(commentID);
                    break;

                default:
                    console.error(
                        'getComment received unexpected comment type "%s"',
                        commentType);
            }

            this._comments[commentID] = comment;
        }

        return this._comments[commentID];
    },

    /**
     * Set the state of a comment.
     *
     * Args:
     *     comment (RB.BaseComment):
     *         The comment to set the state of.
     *
     *     state (string):
     *         The new issue state for the comment.
     */
    _requestState(comment, state) {
        comment.ready({
            ready: () => {
                const oldIssueStatus = comment.get('issueStatus');

                comment.set('issueStatus', state);
                comment.save({
                    attrs: ['issueStatus'],
                    success: (comment, rsp) => {
                        const rspComment = (rsp.diff_comment ||
                                            rsp.file_attachment_comment ||
                                            rsp.screenshot_comment ||
                                            rsp.general_comment);
                        this.trigger('issueStatusUpdated', comment,
                                     oldIssueStatus, rspComment.timestamp);
                    },
                });
            },
        });
    },
});
