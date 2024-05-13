import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    BaseComment,
    CommentIssueStatusType,
    DiffComment,
    FileAttachmentComment,
    GeneralComment,
    Review,
    ReviewRequest,
    ScreenshotComment,
} from 'reviewboard/common';
import {
    type BaseCommentAttrs,
} from 'reviewboard/common/resources/models/baseCommentModel';
import {
    CommentIssueBarView,
    CommentIssueManager,
    CommentIssueManagerCommentType,
} from 'reviewboard/reviews';
import {
    type CommentIssueBarViewOptions
} from 'reviewboard/reviews/views/commentIssueBarView';


interface BuildTestCommentInfo {
    commentType: CommentIssueManagerCommentType;
    CommentCls: typeof BaseComment;
    rspNamespace: string;
    createCommentFunc: keyof Review;
}


suite('rb/reviews/views/CommentIssueBarView', () => {
    const REVIEW_ID = 1;
    const COMMENT_ID = 2;

    let commentIssueManager: CommentIssueManager;
    let view: CommentIssueBarView;
    let review: Review;

    function createComment<
        TComment extends BaseComment,
    >(
        commentInfo: BuildTestCommentInfo,
        attrs: Partial<BaseCommentAttrs>
    ) {
        const comment = new commentInfo.CommentCls(attrs);

        spyOn(comment, 'ready').and.resolveTo();
        spyOn(comment, 'save').and.resolveTo({
            [commentInfo.rspNamespace]: {
                timestamp: '2022-07-05T01:02:03',
            },
        });

        const createCommentFunc = commentInfo.createCommentFunc;

        /*
         * We always want the last-created comment to win,
         * since that's what we're testing with.
         */
        if (jasmine.isSpy(review[createCommentFunc])) {
            review[createCommentFunc].and.returnValue(comment);
        } else {
            spyOn(review, createCommentFunc)
                .and.returnValue(comment);
        }
    }

    function getButton(
        action: string,
    ): HTMLButtonElement {
        const buttonEl = view.el.querySelector<HTMLButtonElement>(
            `.ink-c-button[data-action="${action}"]`);
        expect(buttonEl).toBeTruthy();

        return buttonEl;
    }

    afterEach(() => {
        view.remove();
        view = null;

        commentIssueManager = null;
        review = null;
    });

    function createCommentIssueBarView(
        options?: Partial<CommentIssueBarViewOptions>,
    ): CommentIssueBarView {
        view = new CommentIssueBarView(Object.assign({
            canVerify: true,
            commentID: COMMENT_ID,
            commentIssueManager: commentIssueManager,
            commentType: CommentIssueManagerCommentType.DIFF,
            interactive: true,
            issueStatus: CommentIssueStatusType.OPEN,
            reviewID: REVIEW_ID,
        }, options));

        view.render();

        return view;
    }

    beforeEach(function() {
        const reviewRequest = new ReviewRequest();

        commentIssueManager = new CommentIssueManager({
            reviewRequest: reviewRequest,
        });

        review = reviewRequest.createReview(REVIEW_ID);

        spyOn(reviewRequest, 'ready').and.resolveTo();
        spyOn(reviewRequest, 'createReview').and.callFake(() => review);
        spyOn(review, 'ready').and.resolveTo();
    });

    describe('Actions', () => {
        let comment: BaseComment;

        beforeEach(() => {
            comment = commentIssueManager.getOrCreateComment({
                commentID: 2,
                commentType: CommentIssueManagerCommentType.DIFF,
                reviewID: 1,
            });
            spyOn(comment, 'ready').and.resolveTo();
            spyOn(comment, 'getAuthorUsername').and.returnValue('doc');
        });

        it('Resolving as fixed', done => {
            view = createCommentIssueBarView();

            const resolveButton = getButton('resolve');
            const dropButton = getButton('drop');

            spyOn(commentIssueManager, 'setCommentIssueStatus').and.callFake(
                options => {
                    expect(resolveButton.getAttribute('aria-busy'))
                        .toBe('true');
                    expect(resolveButton.disabled).toBeFalse();
                    expect(dropButton.getAttribute('aria-busy')).toBeNull();
                    expect(dropButton.disabled).toBeTrue();

                    expect(options).toEqual({
                        commentID: COMMENT_ID,
                        commentType: CommentIssueManagerCommentType.DIFF,
                        newIssueStatus: CommentIssueStatusType.RESOLVED,
                        reviewID: REVIEW_ID,
                    });

                    done();
                });

            resolveButton.click();
        });

        it('Dropping', done => {
            view = createCommentIssueBarView();

            const resolveButton = getButton('resolve');
            const dropButton = getButton('drop');

            spyOn(commentIssueManager, 'setCommentIssueStatus').and.callFake(
                options => {
                    expect(resolveButton.getAttribute('aria-busy')).toBeNull();
                    expect(resolveButton.disabled).toBeTrue();
                    expect(dropButton.getAttribute('aria-busy')).toBe('true');
                    expect(dropButton.disabled).toBeFalse();

                    expect(options).toEqual({
                        commentID: COMMENT_ID,
                        commentType: CommentIssueManagerCommentType.DIFF,
                        newIssueStatus: CommentIssueStatusType.DROPPED,
                        reviewID: REVIEW_ID,
                    });

                    done();
                });

            dropButton.click();
        });

        it('Re-opening from resolved', done => {
            comment.set('issueStatus', CommentIssueStatusType.RESOLVED);
            view = createCommentIssueBarView({
                issueStatus: CommentIssueStatusType.RESOLVED,
            });

            const reopenButton = getButton('reopen');

            spyOn(commentIssueManager, 'setCommentIssueStatus').and.callFake(
                options => {
                    expect(reopenButton.getAttribute('aria-busy'))
                        .toBe('true');
                    expect(reopenButton.disabled).toBeFalse();

                    expect(options).toEqual({
                        commentID: COMMENT_ID,
                        commentType: CommentIssueManagerCommentType.DIFF,
                        newIssueStatus: CommentIssueStatusType.OPEN,
                        reviewID: REVIEW_ID,
                    });

                    done();
                });

            reopenButton.click();
        });

        it('Re-opening from dropped', done => {
            comment.set('issueStatus', CommentIssueStatusType.DROPPED);
            view = createCommentIssueBarView({
                issueStatus: CommentIssueStatusType.DROPPED,
            });

            const reopenButton = getButton('reopen');

            spyOn(commentIssueManager, 'setCommentIssueStatus').and.callFake(
                options => {
                    expect(reopenButton.getAttribute('aria-busy'))
                        .toBe('true');
                    expect(reopenButton.disabled).toBeFalse();

                    expect(options).toEqual({
                        commentID: COMMENT_ID,
                        commentType: CommentIssueManagerCommentType.DIFF,
                        newIssueStatus: CommentIssueStatusType.OPEN,
                        reviewID: REVIEW_ID,
                    });

                    done();
                });

            reopenButton.click();
        });

        it('Re-opening from verify-resolved', done => {
            comment.set('issueStatus',
                        CommentIssueStatusType.VERIFYING_RESOLVED);
            view = createCommentIssueBarView({
                issueStatus: CommentIssueStatusType.VERIFYING_RESOLVED,
            });

            const reopenButton = getButton('reopen');

            spyOn(commentIssueManager, 'setCommentIssueStatus').and.callFake(
                options => {
                    expect(reopenButton.getAttribute('aria-busy'))
                        .toBe('true');
                    expect(reopenButton.disabled).toBeFalse();

                    expect(options).toEqual({
                        commentID: COMMENT_ID,
                        commentType: CommentIssueManagerCommentType.DIFF,
                        newIssueStatus: CommentIssueStatusType.OPEN,
                        reviewID: REVIEW_ID,
                    });

                    done();
                });

            reopenButton.click();
        });

        it('Re-opening from verify-dropped', done => {
            comment.set('issueStatus',
                        CommentIssueStatusType.VERIFYING_DROPPED);
            view = createCommentIssueBarView({
                issueStatus: CommentIssueStatusType.VERIFYING_DROPPED,
            });

            const reopenButton = getButton('reopen');

            spyOn(commentIssueManager, 'setCommentIssueStatus').and.callFake(
                options => {
                    expect(reopenButton.getAttribute('aria-busy'))
                        .toBe('true');
                    expect(reopenButton.disabled).toBeFalse();

                    expect(options).toEqual({
                        commentID: COMMENT_ID,
                        commentType: CommentIssueManagerCommentType.DIFF,
                        newIssueStatus: CommentIssueStatusType.OPEN,
                        reviewID: REVIEW_ID,
                    });

                    done();
                });

            reopenButton.click();
        });

        it('Verifying resolved', done => {
            comment.set('issueStatus',
                        CommentIssueStatusType.VERIFYING_RESOLVED);
            comment.get('extraData').require_verification = true;

            view = createCommentIssueBarView({
                issueStatus: CommentIssueStatusType.VERIFYING_RESOLVED,
            });

            const reopenButton = getButton('reopen');
            const resolveButton = getButton('verify-resolved');

            spyOn(commentIssueManager, 'setCommentIssueStatus').and.callFake(
                options => {
                    expect(resolveButton.getAttribute('aria-busy'))
                        .toBe('true');
                    expect(resolveButton.disabled).toBeFalse();

                    expect(reopenButton.getAttribute('aria-busy')).toBeNull();
                    expect(reopenButton.disabled).toBeTrue();

                    expect(options).toEqual({
                        commentID: COMMENT_ID,
                        commentType: CommentIssueManagerCommentType.DIFF,
                        newIssueStatus: CommentIssueStatusType.RESOLVED,
                        reviewID: REVIEW_ID,
                    });

                    done();
                });

            resolveButton.click();
         });

        it('Verifying dropped', done => {
            comment.set('issueStatus',
                        CommentIssueStatusType.VERIFYING_DROPPED);
            comment.get('extraData').require_verification = true;

            view = createCommentIssueBarView({
                issueStatus: CommentIssueStatusType.VERIFYING_DROPPED,
            });

            const reopenButton = getButton('reopen');
            const resolveButton = getButton('verify-dropped');

            spyOn(commentIssueManager, 'setCommentIssueStatus').and.callFake(
                options => {
                    expect(resolveButton.getAttribute('aria-busy'))
                        .toBe('true');
                    expect(resolveButton.disabled).toBeFalse();

                    expect(reopenButton.getAttribute('aria-busy')).toBeNull();
                    expect(reopenButton.disabled).toBeTrue();

                    expect(options).toEqual({
                        commentID: COMMENT_ID,
                        commentType: CommentIssueManagerCommentType.DIFF,
                        newIssueStatus: CommentIssueStatusType.DROPPED,
                        reviewID: REVIEW_ID,
                    });

                    done();
                });

            resolveButton.click();
         });
    });

    describe('Event handling', () => {
        describe('CommentIssueManager.issueStatusUpdated', () => {
            const COMMENT_STATUS = CommentIssueStatusType.OPEN;

            /* We'll override these for our tests. */
            function _buildTests(
                commentInfo: BuildTestCommentInfo,
                otherCommentInfo: BuildTestCommentInfo,
            ) {
                beforeEach(() => {
                    view = createCommentIssueBarView({
                        commentType: commentInfo.commentType,
                    });

                    createComment(commentInfo, {
                        id: COMMENT_ID,
                        issueStatus: CommentIssueStatusType.RESOLVED,
                    });
                });

                it('When comment updated', async () => {
                    await commentIssueManager.setCommentIssueStatus({
                        commentID: COMMENT_ID,
                        commentType: commentInfo.commentType,
                        reviewID: REVIEW_ID,
                        newIssueStatus: CommentIssueStatusType.RESOLVED,
                    });

                    expect(view.el.dataset.issueStatus).toBe('resolved');
                });

                describe('When different comment updated', () => {
                    it('With same ID, different type', async () => {
                        createComment(otherCommentInfo, {
                            id: COMMENT_ID,
                            issueStatus: CommentIssueStatusType.RESOLVED,
                        });

                        await commentIssueManager.setCommentIssueStatus({
                            commentID: COMMENT_ID,
                            commentType: otherCommentInfo.commentType,
                            reviewID: REVIEW_ID,
                            newIssueStatus: CommentIssueStatusType.RESOLVED,
                        });

                        expect(view.el.dataset.issueStatus).toBe('open');
                    });

                    it('With different ID, same type', async () => {
                        createComment(commentInfo, {
                            id: COMMENT_ID + 1,
                            issueStatus: CommentIssueStatusType.RESOLVED,
                        });

                        await commentIssueManager.setCommentIssueStatus({
                            commentID: COMMENT_ID + 1,
                            commentType: commentInfo.commentType,
                            reviewID: REVIEW_ID,
                            newIssueStatus: CommentIssueStatusType.RESOLVED,
                        });

                        expect(view.el.dataset.issueStatus).toBe('open');
                    });
                });
            }

            describe('For diff comments', () => {
                _buildTests(
                    {
                        commentType: CommentIssueManagerCommentType.DIFF,
                        CommentCls: DiffComment,
                        rspNamespace: 'diff_comment',
                        createCommentFunc: 'createDiffComment',
                    },
                    {
                        commentType: CommentIssueManagerCommentType.GENERAL,
                        CommentCls: GeneralComment,
                        rspNamespace: 'general_comment',
                        createCommentFunc: 'createGeneralComment',
                    });
            });

            describe('For general comments', () => {
                _buildTests(
                    {
                        commentType: CommentIssueManagerCommentType.GENERAL,
                        CommentCls: GeneralComment,
                        rspNamespace: 'general_comment',
                        createCommentFunc: 'createGeneralComment',
                    },
                    {
                        commentType: CommentIssueManagerCommentType.DIFF,
                        CommentCls: DiffComment,
                        rspNamespace: 'diff_comment',
                        createCommentFunc: 'createDiffComment',
                    });
            });

            describe('For file attachment comments', () => {
                _buildTests(
                    {
                        commentType:
                            CommentIssueManagerCommentType.FILE_ATTACHMENT,
                        CommentCls: FileAttachmentComment,
                        rspNamespace: 'file_attachment_comment',
                        createCommentFunc: 'createFileAttachmentComment',
                    },
                    {
                        commentType: CommentIssueManagerCommentType.GENERAL,
                        CommentCls: GeneralComment,
                        rspNamespace: 'general_comment',
                        createCommentFunc: 'createGeneralComment',
                    });
            });

            describe('For screenshot comments', () => {
                _buildTests(
                    {
                        commentType: CommentIssueManagerCommentType.SCREENSHOT,
                        CommentCls: ScreenshotComment,
                        rspNamespace: 'screenshot_comment',
                        createCommentFunc: 'createScreenshotComment',
                    },
                    {
                        commentType: CommentIssueManagerCommentType.GENERAL,
                        CommentCls: GeneralComment,
                        rspNamespace: 'general_comment',
                        createCommentFunc: 'createGeneralComment',
                    });
            });
        });
    });

    describe('Issue statuses', () => {
        function testIssueStatus(
            options: {
                interactive: boolean,
                issueStatus: CommentIssueStatusType,
                expectedActions: string[],
                expectedMessage: string,
                canVerify?: boolean,
            }
        ) {
            const issueStatus = options.issueStatus;

            view = createCommentIssueBarView({
                canVerify: !!options.canVerify,
                interactive: options.interactive,
                issueStatus: issueStatus,
            });
            const el = view.el;

            /* Check the buttons. */
            expect(
                Array.from<HTMLButtonElement>(
                    el.querySelectorAll<HTMLButtonElement>('.ink-c-button'))
                .map(buttonEl => buttonEl.dataset.action)
            ).toEqual(options.expectedActions);

            /* Check the message text. */
            const messageEl =
                el.querySelector<HTMLElement>('.rb-c-issue-bar__message');

            expect(messageEl.textContent).toBe(options.expectedMessage);

            /* Check the data attributes. */
            expect(el.dataset.issueStatus).toBe(issueStatus);
        }

        describe('Open', () => {
            it('When interactive', () => {
                testIssueStatus({
                    issueStatus: CommentIssueStatusType.OPEN,
                    interactive: true,
                    expectedActions: ['resolve', 'drop'],
                    expectedMessage: 'An issue was opened.',
                });
            });

            it('When not interactive', () => {
                testIssueStatus({
                    issueStatus: CommentIssueStatusType.OPEN,
                    interactive: false,
                    expectedActions: [],
                    expectedMessage: 'An issue was opened.',
                });
            });
        });

        describe('Dropped', () => {
            it('When interactive', () => {
                testIssueStatus({
                    issueStatus: CommentIssueStatusType.DROPPED,
                    interactive: true,
                    expectedActions: ['reopen'],
                    expectedMessage: 'The issue has been dropped.',
                });
            });

            it('When not interactive', () => {
                testIssueStatus({
                    issueStatus: CommentIssueStatusType.DROPPED,
                    interactive: false,
                    expectedActions: [],
                    expectedMessage: 'The issue has been dropped.',
                });
            });
        });

        describe('Fixed', () => {
            it('When interactive', () => {
                testIssueStatus({
                    issueStatus: CommentIssueStatusType.RESOLVED,
                    interactive: true,
                    expectedActions: ['reopen'],
                    expectedMessage: 'The issue has been resolved.',
                });
            });

            it('When not interactive', () => {
                testIssueStatus({
                    issueStatus: CommentIssueStatusType.RESOLVED,
                    interactive: false,
                    expectedActions: [],
                    expectedMessage: 'The issue has been resolved.',
                });
            });
        });

        describe('Verifying Dropped', () => {
            describe('When interactive', () => {
                it('When can verify', () => {
                    testIssueStatus({
                        canVerify: true,
                        issueStatus: CommentIssueStatusType.VERIFYING_DROPPED,
                        interactive: true,
                        expectedActions: ['reopen', 'verify-dropped'],
                        expectedMessage:
                            'Waiting for verification before dropping...',
                    });
                });

                it('When cannot verify', () => {
                    testIssueStatus({
                        canVerify: false,
                        issueStatus: CommentIssueStatusType.VERIFYING_DROPPED,
                        interactive: true,
                        expectedActions: ['reopen'],
                        expectedMessage:
                            'Waiting for verification before dropping...',
                    });
                });
            });

            it('When not interactive', () => {
                testIssueStatus({
                    issueStatus: CommentIssueStatusType.VERIFYING_DROPPED,
                    interactive: false,
                    expectedActions: [],
                    expectedMessage:
                        'Waiting for verification before dropping...',
                });
            });
        });

        describe('Verifying Fixed', () => {
            describe('When interactive', () => {
                it('When can verify', () => {
                    testIssueStatus({
                        canVerify: true,
                        issueStatus: CommentIssueStatusType.VERIFYING_RESOLVED,
                        interactive: true,
                        expectedActions: ['reopen', 'verify-resolved'],
                        expectedMessage:
                            'Waiting for verification before resolving...',
                    });
                });

                it('When cannot verify', () => {
                    testIssueStatus({
                        canVerify: false,
                        issueStatus: CommentIssueStatusType.VERIFYING_RESOLVED,
                        interactive: true,
                        expectedActions: ['reopen'],
                        expectedMessage:
                            'Waiting for verification before resolving...',
                    });
                });
            });

            it('When not interactive', () => {
                testIssueStatus({
                    issueStatus: CommentIssueStatusType.VERIFYING_RESOLVED,
                    interactive: false,
                    expectedActions: [],
                    expectedMessage:
                        'Waiting for verification before resolving...',
                });
            });
        });
    });
});
