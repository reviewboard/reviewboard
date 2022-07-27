/**
 * Manages issue states for comments on a review request.
 *
 * CommentIssueManager takes care of setting the state of a particular
 * comment issue, and also takes care of notifying callbacks whenever
 * the state is successfully changed.
 *
 * Events:
 *     issueStatusUpdated:
 *         The issue status of a comment has changed.
 *
 *         Args:
 *             comment (RB.BaseComment):
 *                 The comment that changed.
 *
 *             oldIssueStatus (string):
 *                 The old issue status.
 *
 *             timestamp (string):
 *                 The latest timestamp for the comment.
 *
 *             commentType (string):
 *                 The comment type identifier (one of
 *                 :js:attr:`RB.CommentIssueManager.CommentTypes`).
 *
 *                 Version Added:
 *                     4.0.8
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
            const CommentTypes = RB.CommentIssueManager.CommentTypes;
            const reviewRequest = this.get('reviewRequest');
            let comment = null;

            switch (commentType) {
                case CommentTypes.DIFF:
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createDiffComment({id: commentID});
                    break;

                case CommentTypes.SCREENSHOT:
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createScreenshotComment(commentID);
                    break;

                case CommentTypes.FILE_ATTACHMENT:
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createFileAttachmentComment(commentID);
                    break;

                case CommentTypes.GENERAL:
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
     * This will store the new state in the comment on the server, and then
     * notify listeners of the latest comment information.
     *
     * Args:
     *     comment (RB.BaseComment):
     *         The comment to set the state of.
     *
     *     state (string):
     *         The new issue state for the comment.
     */
    async _requestState(comment, state) {
        await comment.ready();

        const oldIssueStatus = comment.get('issueStatus');

        comment.set('issueStatus', state);
        const rsp = await comment.save({
            attrs: ['issueStatus'],
        });

        this._notifyIssueStatusChanged(comment, rsp, oldIssueStatus);
    },

    /**
     * Notify listeners that a comment's issue status changed.
     *
     * This will trigger the ``issueStatusUpdated`` event.
     *
     * Args:
     *     comment (RB.BaseComment):
     *         The comment instance that changed.
     *
     *     rsp (object):
     *         The API response object from saving the comment.
     *
     *     oldIssueStatus (string):
     *         The old issue status.
     */
    _notifyIssueStatusChanged(comment, rsp, oldIssueStatus) {
        const CommentTypes = RB.CommentIssueManager.CommentTypes;
        let rspComment;
        let commentType;

        if (rsp.diff_comment) {
            rspComment = rsp.diff_comment;
            commentType = CommentTypes.DIFF;
        } else if (rsp.general_comment) {
            rspComment = rsp.general_comment;
            commentType = CommentTypes.GENERAL;
        } else if (rsp.file_attachment_comment) {
            rspComment = rsp.file_attachment_comment;
            commentType = CommentTypes.FILE_ATTACHMENT;
        } else if (rsp.screenshot_comment) {
            rspComment = rsp.screenshot_comment;
            commentType = CommentTypes.SCREENSHOT;
        } else {
            console.error(
                'RB.CommentIssueManager._notifyIssueStatusChanged received ' +
                'unexpected comment object "%o"',
                rsp);
            return;
        }

        console.assert(rspComment);
        console.assert(commentType);

        this.trigger('issueStatusUpdated', comment, oldIssueStatus,
                     rspComment.timestamp, commentType);
    },
}, {
    /**
     * A mapping of comment type constants to values.
     *
     * The values should be considered opaque. Callers should use the constants
     * instead.
     *
     * These are only used for functionality in this model and objects
     * interfacing with this model. They should not be used as generic
     * indicators for model classes.
     *
     * Version Added:
     *     4.0.8
     */
    CommentTypes: {
        DIFF: 'diff_comments',
        FILE_ATTACHMENT: 'file_attachment_comments',
        GENERAL: 'general_comments',
        SCREENSHOT: 'screenshot_comments',
    },

    /**
     * Notify listeners that a comment's issue status changed.
     *
     * This will trigger the ``issueStatusUpdated`` event.
     *
     * Args:
     *     comment (RB.BaseComment):
     *         The comment instance that changed.
     *
     *     rsp (object):
     *         The API response object from saving the comment.
     *
     *     oldIssueStatus (string):
     *         The old issue status.
     */
    _notifyIssueStatusChanged(comment, rsp, oldIssueStatus) {
        const CommentTypes = RB.CommentIssueManager.CommentTypes;
        let rspComment;
        let commentType;

        if (rsp.diff_comment) {
            rspComment = rsp.diff_comment;
            commentType = CommentTypes.DIFF;
        } else if (rsp.general_comment) {
            rspComment = rsp.general_comment;
            commentType = CommentTypes.GENERAL;
        } else if (rsp.file_attachment_comment) {
            rspComment = rsp.file_attachment_comment;
            commentType = CommentTypes.FILE_ATTACHMENT;
        } else if (rsp.screenshot_comment) {
            rspComment = rsp.screenshot_comment;
            commentType = CommentTypes.SCREENSHOT;
        } else {
            console.error(
                'RB.CommentIssueManager._notifyIssueStatusChanged received ' +
                'unexpected comment object "%o"',
                rsp);
            return;
        }

        console.assert(rspComment);
        console.assert(commentType);

        this.trigger('issueStatusUpdated', comment, oldIssueStatus,
                     rspComment.timestamp, commentType);
    },
}, {
    /**
     * A mapping of comment type constants to values.
     *
     * The values should be considered opaque. Callers should use the constants
     * instead.
     *
     * These are only used for functionality in this model and objects
     * interfacing with this model. They should not be used as generic
     * indicators for model classes.
     *
     * Version Added:
     *     4.0.8
     */
    CommentTypes: {
        DIFF: 'diff_comments',
        FILE_ATTACHMENT: 'file_attachment_comments',
        GENERAL: 'general_comments',
        SCREENSHOT: 'screenshot_comments',
    },
});
