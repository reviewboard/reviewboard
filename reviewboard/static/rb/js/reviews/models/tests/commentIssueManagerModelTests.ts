import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    CommentIssueStatusType,
    Review,
    ReviewRequest,
} from 'reviewboard/common';
import {
    CommentIssueManager,
    CommentIssueManagerCommentType,
} from 'reviewboard/reviews';


suite('rb/reviews/models/CommentIssueManager', () => {
    let commentIssueManager: CommentIssueManager;
    let reviewRequest: ReviewRequest;
    let review: Review;

    beforeEach(() => {
        reviewRequest = new ReviewRequest();
        commentIssueManager = new CommentIssueManager({
            reviewRequest: reviewRequest,
        });

        review = reviewRequest.createReview(123);

        spyOn(reviewRequest, 'ready').and.resolveTo();
        spyOn(review, 'ready').and.resolveTo();
        spyOn(reviewRequest, 'createReview').and.callFake(() => review);
    });

    describe('Methods', () => {
        describe('getOrCreateComment', () => {
            it('Caches results', () => {
                const comment1 = commentIssueManager.getOrCreateComment({
                    commentID: 123,
                    commentType: CommentIssueManagerCommentType.DIFF,
                    reviewID: 456,
                });

                const comment2 = commentIssueManager.getOrCreateComment({
                    commentID: 123,
                    commentType: CommentIssueManagerCommentType.DIFF,
                    reviewID: 456,
                });

                /* These should be the same instance. */
                expect(comment1).toBe(comment2);
                expect(comment1.cid).toBe(comment2.cid);

                /* These should all trigger new objects. */
                const comment3 = commentIssueManager.getOrCreateComment({
                    commentID: 456,
                    commentType: CommentIssueManagerCommentType.DIFF,
                    reviewID: 456,
                });

                expect(comment1).not.toBe(comment3);
                expect(comment1.cid).not.toBe(comment3.cid);

                const comment4 = commentIssueManager.getOrCreateComment({
                    commentID: 123,
                    commentType: CommentIssueManagerCommentType.GENERAL,
                    reviewID: 456,
                });

                expect(comment1).not.toBe(comment4);
                expect(comment1.cid).not.toBe(comment4.cid);
            });

            it('With diff comments', () => {
                const comment = commentIssueManager.getOrCreateComment({
                    commentID: 123,
                    commentType: CommentIssueManagerCommentType.DIFF,
                    reviewID: 456,
                });

                expect(comment).toBeInstanceOf(RB.DiffComment);
            });
        });

        describe('setCommentIssueStatus', () => {
            it('With diff comment', async () => {
                const onAnyUpdated = jasmine.createSpy('onAnyUpdated');
                const onCommentUpdated = jasmine.createSpy('onCommentUpdated');
                const onOtherUpdated = jasmine.createSpy('onOtherUpdated');
                const onLegacyUpdated = jasmine.createSpy('onLegacyUpdated');

                commentIssueManager.on({
                    'anyIssueStatusUpdated': onAnyUpdated,
                    'issueStatusUpdated:diff_comments:456': onCommentUpdated,
                    'issueStatusUpdated:diff_comments:789': onOtherUpdated,
                    'issueStatusUpdated': onLegacyUpdated,
                });

                const comment = review.createDiffComment({
                    beginLineNum: 1,
                    endLineNum: 2,
                    fileDiffID: 42,
                    id: 456,
                });
                comment.set('issueStatus', CommentIssueStatusType.OPEN);
                spyOn(comment, 'ready').and.resolveTo();
                spyOn(comment, 'save').and.resolveTo({
                    diff_comment: {
                        timestamp: '2024-04-08T01:20:01Z',
                    },
                });
                spyOn(review, 'createDiffComment').and.callFake(() => comment);

                await commentIssueManager.setCommentIssueStatus({
                    commentID: 456,
                    commentType: CommentIssueManagerCommentType.DIFF,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    reviewID: 123,
                });

                expect(comment.get('issueStatus')).toBe(
                    CommentIssueStatusType.RESOLVED);

                expect(comment.save).toHaveBeenCalledWith({
                    attrs: ['issueStatus'],
                });

                expect(onAnyUpdated).toHaveBeenCalledWith({
                    comment: comment,
                    commentType: CommentIssueManagerCommentType.DIFF,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    oldIssueStatus: CommentIssueStatusType.OPEN,
                    timestampStr: '2024-04-08T01:20:01Z',
                });

                expect(onCommentUpdated).toHaveBeenCalledWith({
                    comment: comment,
                    commentType: CommentIssueManagerCommentType.DIFF,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    oldIssueStatus: CommentIssueStatusType.OPEN,
                    timestampStr: '2024-04-08T01:20:01Z',
                });

                expect(onLegacyUpdated).toHaveBeenCalledWith(
                    comment,
                    CommentIssueStatusType.OPEN,
                    '2024-04-08T01:20:01Z',
                    CommentIssueManagerCommentType.DIFF);

                expect(onOtherUpdated).not.toHaveBeenCalled();
            });

            it('With file attachment comment', async () => {
                const onAnyUpdated = jasmine.createSpy('onAnyUpdated');
                const onCommentUpdated = jasmine.createSpy('onCommentUpdated');
                const onOtherUpdated = jasmine.createSpy('onOtherUpdated');
                const onLegacyUpdated = jasmine.createSpy('onLegacyUpdated');

                commentIssueManager.on({
                    'anyIssueStatusUpdated': onAnyUpdated,
                    'issueStatusUpdated:file_attachment_comments:456':
                        onCommentUpdated,
                    'issueStatusUpdated:file_attachment_comments:789':
                        onOtherUpdated,
                    'issueStatusUpdated': onLegacyUpdated,
                });

                const comment = review.createFileAttachmentComment(456);
                comment.set('issueStatus', CommentIssueStatusType.OPEN);
                spyOn(comment, 'ready').and.resolveTo();
                spyOn(comment, 'save').and.resolveTo({
                    file_attachment_comment: {
                        timestamp: '2024-04-08T01:20:01Z',
                    },
                });
                spyOn(review, 'createFileAttachmentComment').and.callFake(
                    () => comment);

                await commentIssueManager.setCommentIssueStatus({
                    commentID: 456,
                    commentType:
                        CommentIssueManagerCommentType.FILE_ATTACHMENT,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    reviewID: 123,
                });

                expect(comment.get('issueStatus')).toBe(
                    CommentIssueStatusType.RESOLVED);

                expect(comment.save).toHaveBeenCalledWith({
                    attrs: ['issueStatus'],
                });

                expect(onAnyUpdated).toHaveBeenCalledWith({
                    comment: comment,
                    commentType:
                        CommentIssueManagerCommentType.FILE_ATTACHMENT,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    oldIssueStatus: CommentIssueStatusType.OPEN,
                    timestampStr: '2024-04-08T01:20:01Z',
                });

                expect(onCommentUpdated).toHaveBeenCalledWith({
                    comment: comment,
                    commentType:
                        CommentIssueManagerCommentType.FILE_ATTACHMENT,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    oldIssueStatus: CommentIssueStatusType.OPEN,
                    timestampStr: '2024-04-08T01:20:01Z',
                });

                expect(onLegacyUpdated).toHaveBeenCalledWith(
                    comment,
                    CommentIssueStatusType.OPEN,
                    '2024-04-08T01:20:01Z',
                    CommentIssueManagerCommentType.FILE_ATTACHMENT);

                expect(onOtherUpdated).not.toHaveBeenCalled();
            });

            it('With general comment', async () => {
                const onAnyUpdated = jasmine.createSpy('onAnyUpdated');
                const onCommentUpdated = jasmine.createSpy('onCommentUpdated');
                const onOtherUpdated = jasmine.createSpy('onOtherUpdated');
                const onLegacyUpdated = jasmine.createSpy('onLegacyUpdated');

                commentIssueManager.on({
                    'anyIssueStatusUpdated': onAnyUpdated,
                    'issueStatusUpdated:general_comments:456':
                        onCommentUpdated,
                    'issueStatusUpdated:general_comments:789':
                        onOtherUpdated,
                    'issueStatusUpdated': onLegacyUpdated,
                });

                const comment = review.createGeneralComment(456);
                comment.set('issueStatus', CommentIssueStatusType.OPEN);
                spyOn(comment, 'ready').and.resolveTo();
                spyOn(comment, 'save').and.resolveTo({
                    general_comment: {
                        timestamp: '2024-04-08T01:20:01Z',
                    },
                });
                spyOn(review, 'createGeneralComment').and.callFake(
                    () => comment);

                await commentIssueManager.setCommentIssueStatus({
                    commentID: 456,
                    commentType: CommentIssueManagerCommentType.GENERAL,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    reviewID: 123,
                });

                expect(comment.get('issueStatus')).toBe(
                    CommentIssueStatusType.RESOLVED);

                expect(comment.save).toHaveBeenCalledWith({
                    attrs: ['issueStatus'],
                });

                expect(onAnyUpdated).toHaveBeenCalledWith({
                    comment: comment,
                    commentType: CommentIssueManagerCommentType.GENERAL,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    oldIssueStatus: CommentIssueStatusType.OPEN,
                    timestampStr: '2024-04-08T01:20:01Z',
                });

                expect(onCommentUpdated).toHaveBeenCalledWith({
                    comment: comment,
                    commentType: CommentIssueManagerCommentType.GENERAL,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    oldIssueStatus: CommentIssueStatusType.OPEN,
                    timestampStr: '2024-04-08T01:20:01Z',
                });

                expect(onLegacyUpdated).toHaveBeenCalledWith(
                    comment,
                    CommentIssueStatusType.OPEN,
                    '2024-04-08T01:20:01Z',
                    CommentIssueManagerCommentType.GENERAL);

                expect(onOtherUpdated).not.toHaveBeenCalled();
            });

            it('With screenshot comment', async () => {
                const onAnyUpdated = jasmine.createSpy('onAnyUpdated');
                const onCommentUpdated = jasmine.createSpy('onCommentUpdated');
                const onOtherUpdated = jasmine.createSpy('onOtherUpdated');
                const onLegacyUpdated = jasmine.createSpy('onLegacyUpdated');

                commentIssueManager.on({
                    'anyIssueStatusUpdated': onAnyUpdated,
                    'issueStatusUpdated:screenshot_comments:456':
                        onCommentUpdated,
                    'issueStatusUpdated:screenshot_comments:789':
                        onOtherUpdated,
                    'issueStatusUpdated': onLegacyUpdated,
                });

                const comment = review.createScreenshotComment(
                    456,   // id
                    42,    // screenshotID
                    0,     // x
                    0,     // y
                    100,   // width
                    100);  // height
                comment.set('issueStatus', CommentIssueStatusType.OPEN);
                spyOn(comment, 'ready').and.resolveTo();
                spyOn(comment, 'save').and.resolveTo({
                    screenshot_comment: {
                        timestamp: '2024-04-08T01:20:01Z',
                    },
                });
                spyOn(review, 'createScreenshotComment').and.callFake(
                    () => comment);

                await commentIssueManager.setCommentIssueStatus({
                    commentID: 456,
                    commentType: CommentIssueManagerCommentType.SCREENSHOT,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    reviewID: 123,
                });

                expect(comment.get('issueStatus')).toBe(
                    CommentIssueStatusType.RESOLVED);

                expect(comment.save).toHaveBeenCalledWith({
                    attrs: ['issueStatus'],
                });

                expect(onAnyUpdated).toHaveBeenCalledWith({
                    comment: comment,
                    commentType: CommentIssueManagerCommentType.SCREENSHOT,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    oldIssueStatus: CommentIssueStatusType.OPEN,
                    timestampStr: '2024-04-08T01:20:01Z',
                });

                expect(onCommentUpdated).toHaveBeenCalledWith({
                    comment: comment,
                    commentType: CommentIssueManagerCommentType.SCREENSHOT,
                    newIssueStatus: CommentIssueStatusType.RESOLVED,
                    oldIssueStatus: CommentIssueStatusType.OPEN,
                    timestampStr: '2024-04-08T01:20:01Z',
                });

                expect(onLegacyUpdated).toHaveBeenCalledWith(
                    comment,
                    CommentIssueStatusType.OPEN,
                    '2024-04-08T01:20:01Z',
                    CommentIssueManagerCommentType.SCREENSHOT);

                expect(onOtherUpdated).not.toHaveBeenCalled();
            });
        });

        describe('makeCommentEventID', () => {
            it('With diff comment', () => {
                const comment = new RB.DiffComment({
                    id: 456,
                });

                expect(commentIssueManager.makeCommentEventID(comment))
                    .toBe('diff_comments:456');
            });

            it('With file attachment comment', () => {
                const comment = new RB.FileAttachmentComment({
                    id: 456,
                });

                expect(commentIssueManager.makeCommentEventID(comment))
                    .toBe('file_attachment_comments:456');
            });

            it('With general comment', () => {
                const comment = new RB.GeneralComment({
                    id: 456,
                });

                expect(commentIssueManager.makeCommentEventID(comment))
                    .toBe('general_comments:456');
            });

            it('With screenshot comment', () => {
                const comment = new RB.ScreenshotComment({
                    id: 456,
                });

                expect(commentIssueManager.makeCommentEventID(comment))
                    .toBe('screenshot_comments:456');
            });
        });
    });
});
