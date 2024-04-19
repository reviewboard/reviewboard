/**
 * Manager for tracking issue statuses of comments on a review request.
 */

import {
    BaseModel,
    spina,
} from '@beanbag/spina';

import {
    type CommentIssueStatusType,
    type BaseComment,
    type ReviewRequest,
} from 'reviewboard/common';
import {
    type BaseCommentResourceData,
} from 'reviewboard/common/resources/models/baseCommentModel';


/**
 * Comment types supported by CommentIssueManager.
 *
 * The values should be considered opaque. Callers should use the constants
 * instead.
 *
 * These are only used for functionality in this model and objects
 * interfacing with this model. They should not be used as generic
 * indicators for model classes.
 *
 * Version Added:
 *     7.0
 */
export enum CommentIssueManagerCommentType {
    DIFF = 'diff_comments',
    FILE_ATTACHMENT = 'file_attachment_comments',
    GENERAL = 'general_comments',
    SCREENSHOT = 'screenshot_comments',
}


/*
 * NOTE: Ideally, we'd have a mapping of the types above to the resource
 *       classes, so that we can automatically infer the right type down
 *       below in getOrCreateComment.
 *
 *       As of this writing (April 7, 2024 -- Review Board 7), we don't
 *       have newer-style classes yet for these comment types, so we can't
 *       actually do this.
 *
 *       This code is being left here for a future implementation, as a
 *       reminder and an exercise to a future developer to address this.
 */
/*
type CommentIssueManagerCommentClasses = {
    [CommentIssueManagerCommentType.DIFF]: DiffComment,
    [CommentIssueManagerCommentType.FILE_ATTACHMENT]: FileAttachmentComment,
    [CommentIssueManagerCommentType.GENERAL]: GeneralComment,
    [CommentIssueManagerCommentType.SCREENSHOT]: ScreenshotComment,
};
*/


/**
 * Options for CommentIssueManager.getOrCreateComment().
 *
 * Version Added:
 *     7.0
 */
export interface GetOrCreateCommentOptions {
    /** The ID of the comment. */
    commentID: number;

    /** The type of the comment. */
    commentType: CommentIssueManagerCommentType;

    /** The ID of the review owning the comment. */
    reviewID: number;
}


/**
 * Options for setting the issue status of a comment.
 *
 * Version Added:
 *     7.0
 */
export interface SetCommentIssueStatusOptions {
    /** The ID of the comment. */
    commentID: number;

    /** The type of the comment. */
    commentType: CommentIssueManagerCommentType;

    /** The new issue status to set. */
    newIssueStatus: CommentIssueStatusType;

    /** The ID of the review owning the comment. */
    reviewID: number;
}


/**
 * Attributes for configuring the manager.
 *
 * Version Added:
 *     7.0
 */
export interface CommentIssueManagerAttrs {
    /** The review request that the issues are filed against. */
    reviewRequest: ReviewRequest;
}


/**
 * Event data for an issueStatusUpdated-like event.
 *
 * Version Added:
 *     7.0
 */
export interface IssueStatusUpdatedEventData {
    /** The comment instance that was updated. */
    comment: BaseComment;

    /** The type of the comment. */
    commentType: CommentIssueManagerCommentType;

    /** The comment's new issue status. */
    newIssueStatus: CommentIssueStatusType;

    /** The comment's old issue status. */
    oldIssueStatus: CommentIssueStatusType;

    /** The string-encoded timestamp of the event. */
    timestampStr: string;
}


/**
 * Manages issue states for comments on a review request.
 *
 * CommentIssueManager takes care of setting the state of a particular
 * comment issue, and also takes care of notifying callbacks whenever
 * the state is successfully changed.
 *
 * Events:
 *     anyIssueStatusUpdated:
 *         The issue status of a comment has changed.
 *
 *         This can be used to listen to changes to any comment tracked
 *         by this manager.
 *
 *         Version Added:
 *             7.0
 *
 *         Args:
 *             eventData (object):
 *                 Data on the event.
 *
 *                 See :js:class:`IssueStatusUpdatedEventData` for details.
 *
 *     issueStatusUpdated:{comment_type}:{comment_id}:
 *         The issue status of a specific comment has changed.
 *
 *         This can be used to listen to changes to a specified comment tracked
 *         by this manager. Callers should form the event type by using
 *         the string value of a :js:class:`CommentIssueManagerCommentType`
 *         enum and of the comment ID.
 *
 *         Version Added:
 *             7.0
 *
 *         Args:
 *             eventData (object):
 *                 Data on the event.
 *
 *                 See :js:class:`IssueStatusUpdatedEventData` for details.
 *
 *     issueStatusUpdated:
 *         The issue status of a comment has changed.
 *
 *         Deprecated:
 *             7.0:
 *             Callers should use ``anyIssueStatusUpdated`` or
 *             :samp:`issueStatusUpdated:{comment_type}:{comment_id}` instead.
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
@spina
export class CommentIssueManager extends BaseModel<
    CommentIssueManagerAttrs
>{
    static defaults: CommentIssueManagerAttrs = {
        reviewRequest: null,
    };

    /**
     * Deprecated mapping of comment type constants to values.
     *
     * Callers should use :js:class:`CommentIssueManagerCommentType` instead.
     *
     * Deprecated:
     *     7.0
     *
     * Version Added:
     *     4.0.8
     */
    static CommentTypes = CommentIssueManagerCommentType;

    /**********************
     * Instance variables *
     **********************/

    /**
     * A mapping of internal comment type/ID keys to comment instances.
     *
     * Version Added:
     *     7.0
     */
    #comments: { [key: string]: BaseComment } = {};

    /**
     * Return an ID used be comment-specific events.
     *
     * This can help with creating a comment-specific ID for the
     * ``issueStatusUpdated`` event.
     *
     * Version Added:
     *     7.0
     *
     * Args:
     *     comment (RB.BaseComment):
     *         The comment the ID will represent.
     *
     * Returns:
     *     string:
     *     The event ID.
     */
    makeCommentEventID(
        comment: BaseComment,
    ): string {
        let commentType: CommentIssueManagerCommentType;

        if (comment instanceof RB.DiffComment) {
            commentType = CommentIssueManagerCommentType.DIFF;
        } else if (comment instanceof RB.FileAttachmentComment) {
            commentType = CommentIssueManagerCommentType.FILE_ATTACHMENT;
        } else if (comment instanceof RB.GeneralComment) {
            commentType = CommentIssueManagerCommentType.GENERAL;
        } else if (comment instanceof RB.ScreenshotComment) {
            commentType = CommentIssueManagerCommentType.SCREENSHOT;
        } else {
            console.error(
                'RB.CommentIssueManager.makeCommentEventID received ' +
                'unexpected comment object "%o"',
                comment);
            return null;
        }

        return `${commentType}:${comment.id}`;
    }

    /**
     * Set the state for a comment.
     *
     * Deprecated:
     *     7.0:
     *     Callers should use :js:meth:`setCommentIssueStatus` instead.
     *     This method is expected to be removed in Review Board 9.
     *
     * Args:
     *     reviewID (number):
     *         The ID of the review the comment belongs to.
     *
     *     commentID (number):
     *         The ID of the comment.
     *
     *     commentType (CommentIssueManagerCommentType):
     *         The type of the comment.
     *
     *     state (CommentIssueStatusType):
     *         The new state for the comment's issue.
     */
    setCommentState(
        reviewID: number,
        commentID: number,
        commentType: CommentIssueManagerCommentType,
        state: CommentIssueStatusType,
    ) {
        console.group('CommentIssueManager.setCommentState() is deprecated.');
        console.warn('This will be removed in Review Board 9. Please use '+
                     'setCommentIssueStatus() instead.');
        console.trace();
        console.groupEnd();

        this.setCommentIssueStatus({
            commentID: commentID,
            commentType: commentType,
            newIssueStatus: state,
            reviewID: reviewID,
        });
    }

    /**
     * Set the issue status for a comment.
     *
     * The operation will be performed asynchronously. Callers can await
     * this call, or listen to an event to know when the issue status is
     * updated.
     *
     * Args:
     *     options (SetCommentIssueStatusOptions):
     *         The options for identifying the comment and setting the
     *         issue status.
     */
    async setCommentIssueStatus(
        options: SetCommentIssueStatusOptions,
    ): Promise<void> {
        const comment = await this.getOrCreateComment({
            reviewID: options.reviewID,
            commentID: options.commentID,
            commentType: options.commentType,
        });

        await this.#updateIssueStatus(comment, options.newIssueStatus);
    }

    /**
     * Retrieve the model for a given comment.
     *
     * This will either generate the appropriate comment object based on
     * ``commentType``, or grab the comment from a cache if it's been generated
     * before.
     *
     * Deprecated:
     *     7.0:
     *     Callers should use :js:meth:`getOrCreateComment` instead.
     *     This method is expected to be removed in Review Board 9.
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
     *         This is a valid value in
     *         :js:class:`CommentIssueManagerCommentType`.
     *
     * Returns:
     *     RB.BaseComment:
     *     The comment model.
     */
    getComment(
        reviewID: number,
        commentID: number,
        commentType: CommentIssueManagerCommentType,
    ): BaseComment {
        console.group('CommentIssueManager.getComment() is deprecated.');
        console.warn('This will be removed in Review Board 9. Please use '+
                     'getOrCreateComment() instead.');
        console.trace();
        console.groupEnd();

        return this.getOrCreateComment({
            commentID: commentID,
            commentType: commentType,
            reviewID: reviewID,
        });
    }

    /**
     * Retrieve the model for a given comment.
     *
     * This will either generate the appropriate comment object based on
     * ``commentType``, or grab the comment from a cache if it's been generated
     * before.
     *
     * Args:
     *     options (GetOrCreateCommentOptions):
     *         The options for identifying or creating the comment.
     *
     * Returns:
     *     RB.BaseComment:
     *     The comment model.
     */
    getOrCreateComment<
        TComment extends BaseComment = BaseComment,
    >(
        options: GetOrCreateCommentOptions,
    ): TComment {
        const commentID = options.commentID;
        const commentType = options.commentType;
        const key = `${commentType}-${commentID}`;
        let comment = this.#comments[key];

        if (!comment) {
            const reviewID = options.reviewID;
            const reviewRequest = this.get('reviewRequest');

            switch (commentType) {
                case CommentIssueManagerCommentType.DIFF:
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createDiffComment({
                            beginLineNum: null,
                            endLineNum: null,
                            fileDiffID: null,
                            id: commentID,
                        });
                    break;

                case CommentIssueManagerCommentType.SCREENSHOT:
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createScreenshotComment(commentID, null, null, null,
                                                 null, null);
                    break;

                case CommentIssueManagerCommentType.FILE_ATTACHMENT:
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createFileAttachmentComment(commentID, null);
                    break;

                case CommentIssueManagerCommentType.GENERAL:
                    comment = reviewRequest
                        .createReview(reviewID)
                        .createGeneralComment(commentID);
                    break;

                default:
                    console.error(
                        'getComment received unexpected comment type "%s"',
                        commentType);
            }

            this.#comments[key] = comment;
        }

        return comment as TComment;
    }

    /**
     * Update the issue status of a comment.
     *
     * This will store the new state in the comment on the server, and then
     * notify listeners of the latest comment information.
     *
     * Args:
     *     comment (RB.BaseComment):
     *         The comment to set the state of.
     *
     *     newIssueStatus (string):
     *         The new issue status for the comment.
     */
    async #updateIssueStatus(
        comment: BaseComment,
        newIssueStatus: CommentIssueStatusType,
    ) {
        await comment.ready();
        const oldIssueStatus = comment.get('issueStatus');

        /* Save the new status. */
        comment.set('issueStatus', newIssueStatus);

        const rsp = await comment.save({
            attrs: ['issueStatus'],
        });

        /* Notify listeners. */
        this.#notifyIssueStatusChanged(comment, rsp, oldIssueStatus);
    }

    /**
     * Notify listeners that a comment's issue status changed.
     *
     * This will trigger the legacy ``issueStatusUpdated`` event and the
     * modern ``anyIssueStatusUpdated`` and
     * :samp:`issueStatusUpdated:{comment_type}:{comment_id}` events.
     *
     * Args:
     *     comment (RB.BaseComment):
     *         The comment instance that changed.
     *
     *     rsp (object):
     *         The API response object from saving the comment.
     *
     *     oldIssueStatus (CommentIssueStatusType):
     *         The old issue status.
     */
    #notifyIssueStatusChanged(
        comment: BaseComment,
        rsp: any,
        oldIssueStatus: CommentIssueStatusType,
    ) {
        let rspComment: BaseCommentResourceData;
        let commentType: CommentIssueManagerCommentType;

        if (rsp.diff_comment) {
            rspComment = rsp.diff_comment;
            commentType = CommentIssueManagerCommentType.DIFF;
        } else if (rsp.general_comment) {
            rspComment = rsp.general_comment;
            commentType = CommentIssueManagerCommentType.GENERAL;
        } else if (rsp.file_attachment_comment) {
            rspComment = rsp.file_attachment_comment;
            commentType = CommentIssueManagerCommentType.FILE_ATTACHMENT;
        } else if (rsp.screenshot_comment) {
            rspComment = rsp.screenshot_comment;
            commentType = CommentIssueManagerCommentType.SCREENSHOT;
        } else {
            console.error(
                'RB.CommentIssueManager.#notifyIssueStatusChanged received ' +
                'unexpected comment object "%o"',
                rsp);
            return;
        }

        console.assert(rspComment);
        console.assert(commentType);

        /* Trigger the modern events. */
        const eventPayload: IssueStatusUpdatedEventData = {
            comment: comment,
            commentType: commentType,
            newIssueStatus: comment.get('issueStatus'),
            oldIssueStatus: oldIssueStatus,
            timestampStr: rspComment.timestamp,
        }

        this.trigger('anyIssueStatusUpdated', eventPayload);
        this.trigger(`issueStatusUpdated:${commentType}:${comment.id}`,
                     eventPayload);

        /* Deprecated as of Review Board 7.0. */
        this.trigger('issueStatusUpdated', comment, oldIssueStatus,
                     rspComment.timestamp, commentType);
    }
}
