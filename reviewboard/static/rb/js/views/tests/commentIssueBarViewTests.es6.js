suite('rb/views/CommentIssueBarView', function() {
    const CommentTypes = RB.CommentIssueManager.CommentTypes;
    let commentIssueManager;
    let view;
    let $dropButton;
    let $reopenButton;
    let $fixedButton;
    let $verifyFixedButton;
    let $verifyDroppedButton;

    beforeEach(function() {
        commentIssueManager = new RB.CommentIssueManager({
            reviewRequest: new RB.ReviewRequest(),
        });
        view = new RB.CommentIssueBarView({
            commentIssueManager: commentIssueManager,
            issueStatus: 'open',
            reviewID: 1,
            commentID: 2,
            commentType: CommentTypes.DIFF,
            interactive: true,
            canVerify: true,
        });
        view.render().$el.appendTo($testsScratch);

        $dropButton = view._$buttons.filter('.drop');
        $reopenButton = view._$buttons.filter('.reopen');
        $fixedButton = view._$buttons.filter('.resolve');
        $verifyFixedButton = view._$buttons.filter('.verify-resolved');
        $verifyDroppedButton = view._$buttons.filter('.verify-dropped');
    });

    describe('Actions', function() {
        let comment;

        beforeEach(function() {
            expect(view._$buttons.prop('disabled')).toBe(false);

            comment = commentIssueManager.getComment(1, 2, CommentTypes.DIFF);
            spyOn(comment, 'ready').and.resolveTo();
            spyOn(comment, 'getAuthorUsername').and.returnValue('doc');
        });

        it('Resolving as fixed', function(done) {
            spyOn(commentIssueManager, 'setCommentState').and.callFake(
                (reviewID, commentID, commentType, state) => {
                    expect(view._$buttons.prop('disabled')).toBe(true);
                    expect(reviewID).toBe(1);
                    expect(commentID).toBe(2);
                    expect(commentType).toBe(CommentTypes.DIFF);
                    expect(state).toBe('resolved');

                    done();
                });

            $fixedButton.click();
        });

        it('Dropping', function(done) {
            spyOn(commentIssueManager, 'setCommentState').and.callFake(
                (reviewID, commentID, commentType, state) => {
                    expect(view._$buttons.prop('disabled')).toBe(true);
                    expect(reviewID).toBe(1);
                    expect(commentID).toBe(2);
                    expect(commentType).toBe(CommentTypes.DIFF);
                    expect(state).toBe('dropped');

                    done();
                });

            $dropButton.click();
        });

        it('Re-opening', function(done) {
            spyOn(commentIssueManager, 'setCommentState').and.callFake(
                (reviewID, commentID, commentType, state) => {
                    expect(view._$buttons.prop('disabled')).toBe(true);
                    expect(reviewID).toBe(1);
                    expect(commentID).toBe(2);
                    expect(commentType).toBe(CommentTypes.DIFF);
                    expect(state).toBe('open');

                    done();
                });

            view._showStatus(RB.BaseComment.STATE_RESOLVED);

            $reopenButton.click();
        });

        it('Resolving with verification', function(done) {
            spyOn(commentIssueManager, 'setCommentState').and.callFake(
                (reviewID, commentID, commentType, state) => {
                    expect(view._$buttons.prop('disabled')).toBe(true);
                    expect(reviewID).toBe(1);
                    expect(commentID).toBe(2);
                    expect(commentType).toBe(CommentTypes.DIFF);
                    expect(state).toBe('verifying-resolved');
                    done();
                });

            comment.get('extraData').require_verification = true;

            $fixedButton.click();
         });

        it('Dropping with verification', function(done) {
            spyOn(commentIssueManager, 'setCommentState').and.callFake(
                (reviewID, commentID, commentType, state) => {
                    expect(view._$buttons.prop('disabled')).toBe(true);
                    expect(reviewID).toBe(1);
                    expect(commentID).toBe(2);
                    expect(commentType).toBe(CommentTypes.DIFF);
                    expect(state).toBe('verifying-dropped');

                    done();
                });

            comment.get('extraData').require_verification = true;

            $dropButton.click();
         });
    });

    describe('Event handling', function() {
        describe('CommentIssueManager.issueStatusUpdated', function() {
            const COMMENT_ID = 2;
            const COMMENT_STATUS = 'open';

            /* We'll override these for our tests. */
            function _buildTests(commentType, CommentCls, rspNamespace,
                                 OtherCommentCls, otherRspNamespace) {
                beforeEach(function() {
                    view = new RB.CommentIssueBarView({
                        commentIssueManager: commentIssueManager,
                        issueStatus: COMMENT_STATUS,
                        reviewID: 1,
                        commentID: COMMENT_ID,
                        commentType: commentType,
                        interactive: true,
                        canVerify: true,
                    });
                    view.render().$el.appendTo($testsScratch);
                    spyOn(view, '_showStatus');
                });

                it('When comment updated', function() {
                    const comment = new CommentCls({
                        id: COMMENT_ID,
                        issueStatus: 'resolved',
                    });

                    const rsp = {};
                    rsp[rspNamespace] = {
                        timestamp: '2022-07-05T01:02:03',
                    };

                    commentIssueManager._notifyIssueStatusChanged(
                        comment, rsp, COMMENT_STATUS);

                    expect(view._showStatus).toHaveBeenCalledWith('resolved');
                });

                describe('When different comment updated', function() {
                    it('With same ID, different type', function() {
                        const comment = new OtherCommentCls({
                            id: COMMENT_ID,
                            issueStatus: 'resolved',
                        });

                        const rsp = {};
                        rsp[otherRspNamespace] = {
                            timestamp: '2022-07-05T01:02:03',
                        };

                        commentIssueManager._notifyIssueStatusChanged(
                            comment, rsp, COMMENT_STATUS);

                        expect(view._showStatus).not.toHaveBeenCalled();
                    });

                    it('With different ID, same type', function() {
                        const comment = new CommentCls({
                            id: COMMENT_ID + 1,
                            issueStatus: 'resolved',
                        });

                        const rsp = {};
                        rsp[rspNamespace] = {
                            timestamp: '2022-07-05T01:02:03',
                        };

                        commentIssueManager._notifyIssueStatusChanged(
                            comment, rsp, COMMENT_STATUS);

                        expect(view._showStatus).not.toHaveBeenCalled();
                    });
                });
            }

            describe('For diff comments', function() {
                _buildTests(CommentTypes.DIFF,
                            RB.DiffComment,
                            'diff_comment',
                            RB.GeneralComment,
                            'general_comment');
            });

            describe('For general comments', function() {
                _buildTests(CommentTypes.GENERAL,
                            RB.GeneralComment,
                            'general_comment',
                            RB.DiffComment,
                            'diff_comment');
            });

            describe('For file attachment comments', function() {
                _buildTests(CommentTypes.FILE_ATTACHMENT,
                            RB.FileAttachmentComment,
                            'file_attachment_comment',
                            RB.DiffComment,
                            'diff_comment');
            });

            describe('For screenshot comments', function() {
                _buildTests(CommentTypes.SCREENSHOT,
                            RB.ScreenshotComment,
                            'screenshot_comment',
                            RB.GeneralComment,
                            'general_comment');
            });
        });
    });

    describe('Issue states', function() {
        describe('Open', function() {
            beforeEach(function() {
                view._showStatus(RB.BaseComment.STATE_OPEN);
            });

            it('CSS class', function() {
                expect(view._$state.hasClass('open')).toBe(true);
                expect(view._$state.hasClass('resolved')).toBe(false);
                expect(view._$state.hasClass('dropped')).toBe(false);
                expect(view._$state.hasClass('verifying-resolved')).toBe(false);
                expect(view._$state.hasClass('verifying-dropped')).toBe(false);
            });

            it('Text', function() {
                expect(view._$message.text()).toBe('An issue was opened.');
            });

            describe('Button visibility', function() {
                it('"Drop" shown', function() {
                    expect($dropButton.is(':visible')).toBe(true);
                });

                it('"Fixed" shown', function() {
                    expect($fixedButton.is(':visible')).toBe(true);
                });

                it('"Re-open" hidden', function() {
                    expect($reopenButton.is(':visible')).toBe(false);
                });

                it('"Verify Fixed" hidden', function() {
                    expect($verifyFixedButton.is(':visible')).toBe(false);
                });

                it('"Verify Dropped" hidden', function() {
                    expect($verifyDroppedButton.is(':visible')).toBe(false);
                });
            });
        });

        describe('Fixed', function() {
            beforeEach(function() {
                view._showStatus(RB.BaseComment.STATE_RESOLVED);
            });

            it('CSS class', function() {
                expect(view._$state.hasClass('open')).toBe(false);
                expect(view._$state.hasClass('resolved')).toBe(true);
                expect(view._$state.hasClass('dropped')).toBe(false);
                expect(view._$state.hasClass('verifying-resolved')).toBe(false);
                expect(view._$state.hasClass('verifying-dropped')).toBe(false);
            });

            it('Text', function() {
                expect(view._$message.text()).toBe(
                    'The issue has been resolved.');
            });

            describe('Button visibility', function() {
                it('"Drop" hidden', function() {
                    expect($dropButton.is(':visible')).toBe(false);
                });

                it('"Fixed" hidden', function() {
                    expect($fixedButton.is(':visible')).toBe(false);
                });

                it('"Re-open" shown', function() {
                    expect($reopenButton.is(':visible')).toBe(true);
                });

                it('"Verify Fixed" hidden', function() {
                    expect($verifyFixedButton.is(':visible')).toBe(false);
                });

                it('"Verify Dropped" hidden', function() {
                    expect($verifyDroppedButton.is(':visible')).toBe(false);
                });
            });
        });

        describe('Dropped', function() {
            beforeEach(function() {
                view._showStatus(RB.BaseComment.STATE_DROPPED);
            });

            it('CSS class', function() {
                expect(view._$state.hasClass('open')).toBe(false);
                expect(view._$state.hasClass('resolved')).toBe(false);
                expect(view._$state.hasClass('dropped')).toBe(true);
                expect(view._$state.hasClass('verifying-resolved')).toBe(false);
                expect(view._$state.hasClass('verifying-dropped')).toBe(false);
            });

            it('Text', function() {
                expect(view._$message.text()).toBe(
                    'The issue has been dropped.');
            });

            describe('Button visibility', function() {
                it('"Drop" hidden', function() {
                    expect($dropButton.is(':visible')).toBe(false);
                });

                it('"Fixed" hidden', function() {
                    expect($fixedButton.is(':visible')).toBe(false);
                });

                it('"Re-open" shown', function() {
                    expect($reopenButton.is(':visible')).toBe(true);
                });

                it('"Verify Fixed" hidden', function() {
                    expect($verifyFixedButton.is(':visible')).toBe(false);
                });

                it('"Verify Dropped" hidden', function() {
                    expect($verifyDroppedButton.is(':visible')).toBe(false);
                });
            });
        });

        describe('Verifying Fixed', function() {
            beforeEach(function() {
                view._showStatus(RB.BaseComment.STATE_VERIFYING_RESOLVED);
            });

            it('CSS class', function() {
                expect(view._$state.hasClass('open')).toBe(false);
                expect(view._$state.hasClass('resolved')).toBe(false);
                expect(view._$state.hasClass('dropped')).toBe(false);
                expect(view._$state.hasClass('verifying-resolved')).toBe(true);
                expect(view._$state.hasClass('verifying-dropped')).toBe(false);
            });

            it('Text', function() {
                expect(view._$message.text()).toBe(
                    'Waiting for verification before resolving...');
            });

            describe('Button visibility', function() {
                it('"Drop" hidden', function() {
                    expect($dropButton.is(':visible')).toBe(false);
                });

                it('"Fixed" hidden', function() {
                    expect($fixedButton.is(':visible')).toBe(false);
                });

                it('"Re-open" shown', function() {
                    expect($reopenButton.is(':visible')).toBe(true);
                });

                it('"Verify Fixed" shown', function() {
                    expect($verifyFixedButton.is(':visible')).toBe(true);
                });

                it('"Verify Dropped" hidden', function() {
                    expect($verifyDroppedButton.is(':visible')).toBe(false);
                });
            });
        });

        describe('Verifying Dropped', function() {
            beforeEach(function() {
                view._showStatus(RB.BaseComment.STATE_VERIFYING_DROPPED);
            });

            it('CSS class', function() {
                expect(view._$state.hasClass('open')).toBe(false);
                expect(view._$state.hasClass('resolved')).toBe(false);
                expect(view._$state.hasClass('dropped')).toBe(false);
                expect(view._$state.hasClass('verifying-resolved')).toBe(false);
                expect(view._$state.hasClass('verifying-dropped')).toBe(true);
            });

            it('Text', function() {
                expect(view._$message.text()).toBe(
                    'Waiting for verification before dropping...');
            });

            describe('Button visibility', function() {
                it('"Drop" hidden', function() {
                    expect($dropButton.is(':visible')).toBe(false);
                });

                it('"Fixed" hidden', function() {
                    expect($fixedButton.is(':visible')).toBe(false);
                });

                it('"Re-open" shown', function() {
                    expect($reopenButton.is(':visible')).toBe(true);
                });

                it('"Verify Fixed" hidden', function() {
                    expect($verifyFixedButton.is(':visible')).toBe(false);
                });

                it('"Verify Dropped" shown', function() {
                    expect($verifyDroppedButton.is(':visible')).toBe(true);
                });
            });
        });
    });
});
