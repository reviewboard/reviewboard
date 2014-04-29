suite('rb/views/CommentIssueBarView', function() {
    var commentIssueManager,
        statuses = RB.CommentIssueBarView.prototype,
        view,
        $dropButton,
        $reopenButton,
        $fixedButton;


    beforeEach(function() {
        commentIssueManager = new RB.CommentIssueManager();
        view = new RB.CommentIssueBarView({
            commentIssueManager: commentIssueManager,
            issueStatus: 'open',
            reviewID: 1,
            commentID: 2,
            commentType: 'diff',
            interactive: true
        });
        view.render().$el.appendTo($testsScratch);

        $dropButton = view._$buttons.filter('.drop');
        $reopenButton = view._$buttons.filter('.reopen');
        $fixedButton = view._$buttons.filter('.resolve');
    });

    describe('Actions', function() {
        beforeEach(function() {
            spyOn(commentIssueManager, 'setCommentState');
            expect(view._$buttons.prop('disabled')).toBe(false);
        });

        it('Resolving as fixed', function() {
            $fixedButton.click();

            expect(view._$buttons.prop('disabled')).toBe(true);

            expect(commentIssueManager.setCommentState)
                .toHaveBeenCalledWith(1, 2, 'diff', 'resolved');
        });

        it('Dropping', function() {
            $dropButton.click();

            expect(view._$buttons.prop('disabled')).toBe(true);

            expect(commentIssueManager.setCommentState)
                .toHaveBeenCalledWith(1, 2, 'diff', 'dropped');
        });

        it('Re-opening', function() {
            view._showStatus(statuses.STATUS_FIXED);

            $reopenButton.click();

            expect(view._$buttons.prop('disabled')).toBe(true);

            expect(commentIssueManager.setCommentState)
                .toHaveBeenCalledWith(1, 2, 'diff', 'open');
        });
    });

    describe('Event handling', function() {
        describe('CommentIssueManager.issueStatusUpdated', function() {
            beforeEach(function() {
                spyOn(view, '_showStatus');
            });

            it('When comment updated', function() {
                var comment = new RB.DiffComment({
                    id: 2,
                    issueStatus: 'resolved'
                });

                commentIssueManager.trigger('issueStatusUpdated', comment);

                expect(view._showStatus).toHaveBeenCalledWith('resolved');
            });

            it('When different comment updated', function() {
                var comment = new RB.DiffComment({
                    id: 10,
                    issueStatus: 'resolved'
                });

                commentIssueManager.trigger('issueStatusUpdated', comment);

                expect(view._showStatus).not.toHaveBeenCalled();
            });
        });
    });

    describe('Issue states', function() {
        describe('Open', function() {
            beforeEach(function() {
                view._showStatus(statuses.STATUS_OPEN);
            });

            it('CSS class', function() {
                expect(view._$state.hasClass('open')).toBe(true);
                expect(view._$state.hasClass('resolved')).toBe(false);
                expect(view._$state.hasClass('dropped')).toBe(false);
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
            });
        });

        describe('Fixed', function() {
            beforeEach(function() {
                view._showStatus(statuses.STATUS_FIXED);
            });

            it('CSS class', function() {
                expect(view._$state.hasClass('open')).toBe(false);
                expect(view._$state.hasClass('resolved')).toBe(true);
                expect(view._$state.hasClass('dropped')).toBe(false);
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
            });
        });

        describe('Dropped', function() {
            beforeEach(function() {
                view._showStatus(statuses.STATUS_DROPPED);
            });

            it('CSS class', function() {
                expect(view._$state.hasClass('open')).toBe(false);
                expect(view._$state.hasClass('resolved')).toBe(false);
                expect(view._$state.hasClass('dropped')).toBe(true);
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
            });
        });
    });
});
