/*
 * commentIssueManager takes care of setting the state of a particular
 * comment issue, and also takes care of notifying callbacks whenever
 * the state is successfully changed.
 */
RB.CommentIssueManager = Backbone.Model.extend({
    defaults: {
        reviewRequest: null
    },

    initialize: function() {
        this._callbacks = {};
        this._comments = {};
    },

    /*
     * setCommentState - set the state of comment issue
     * @param reviewID the id for the review that the comment belongs to
     * @param commentID the id of the comment with the issue
     * @param commentType the type of comment, either "diff_comments",
     *                     "screenshot_comments", or "file_attachment_comments".
     * @param state the state to set the comment issue to - either
     *              "open", "resolved", or "dropped"
     */
    setCommentState: function(reviewID, commentID, commentType, state) {
        var comment = this._getComment(reviewID, commentID, commentType);
        this._requestState(comment, state);
    },

    /*
     * registerCallback - allows clients to register callbacks to be
     * notified when a particular comment state is updated.
     * @param commentID the id of the comment to be notified about
     * @param callback a function of the form:
     *                 function(issue_state) {}
     */
    registerCallback: function(commentID, callback) {
        if (!this._callbacks[commentID]) {
            this._callbacks[commentID] = [];
        }

        this._callbacks[commentID].push(callback);
    },

    /*
     * A helper function to either generate the appropriate
     * comment object based on commentType, or to grab the
     * comment from a cache if it's been generated before.
     */
    _getComment: function(reviewID, commentID, commentType) {
        if (!this._comments[commentID]) {
            var comment = null,
                reviewRequest = this.get('reviewRequest');

            if (commentType === "diff_comments") {
                comment = reviewRequest
                    .createReview(reviewID)
                    .createDiffComment(commentID);
            } else if (commentType === "screenshot_comments") {
                comment = reviewRequest
                    .createReview(reviewID)
                    .createScreenshotComment(commentID);
            } else if (commentType === "file_attachment_comments") {
                comment = reviewRequest
                    .createReview(reviewID)
                    .createFileAttachmentComment(commentID);
            } else {
                console.log("getComment received unexpected context type '%s'",
                            commentType);
            }

            this._comments[commentID] = comment;
        }

        return this._comments[commentID];
    },

    // Helper function to set the state of a comment
    _requestState: function(comment, state) {
        var self = this;

        comment.ready(function() {
            var oldIssueStatus = comment.issue_status;

            comment.issue_status = state;
            comment.save({
                success: function(rsp) {
                    var rspComment = (rsp.diff_comment ||
                                      rsp.file_attachment_comment ||
                                      rsp.screenshot_comment);
                    self._notifyCallbacks(comment.id,
                                          comment.issue_status,
                                          oldIssueStatus,
                                          rspComment.timestamp);

                    /*
                     * We don't want the current user to receive the
                     * notification that the review request has been
                     * updated, since they themselves updated the
                     * issue status.
                     */
                    if (rsp.last_activity_time) {
                        self.get('reviewRequest').markUpdated(
                            rsp.last_activity_time);
                    }
                }
            });
        });
    },

    /*
     * Helper function that notifies all callbacks registered for
     * a particular comment
     */
    _notifyCallbacks: function(commentID, issueStatus, oldIssueStatus,
                               lastUpdated) {
        _.each(this._callbacks[commentID], function(callback) {
            callback(issueStatus, oldIssueStatus, lastUpdated);
        });
    }
});
