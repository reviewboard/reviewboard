suite('rb/models/CommentEditor', function() {
    var editor,
        reviewRequest,
        comment;

    function createComment() {
        return new RB.BaseComment({
            parentObject: new RB.BaseResource({
                'public': true
            })
        });
    }

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest();

        editor = new RB.CommentEditor({
            canEdit: true,
            reviewRequest: reviewRequest
        });
    });

    describe('Attribute defaults', function() {
        describe('canEdit', function() {
            it('When logged in and hasDraft=false', function() {
                RB.UserSession.instance.set('authenticated', true);

                editor = new RB.CommentEditor({
                    reviewRequest: reviewRequest
                });
                expect(editor.get('canEdit')).toBe(true);
            });

            it('When logged in and hasDraft=true', function() {
                RB.UserSession.instance.set('authenticated', true);
                reviewRequest.set('hasDraft', true);

                editor = new RB.CommentEditor({
                    reviewRequest: reviewRequest
                });
                expect(editor.get('canEdit')).toBe(false);
            });

            it('When logged out', function() {
                RB.UserSession.instance.set('authenticated', false);

                editor = new RB.CommentEditor({
                    reviewRequest: reviewRequest
                });
                expect(editor.get('canEdit')).toBe(false);
            });

            it('With explicitly set value', function() {
                RB.UserSession.instance.set('authenticated', false);

                editor = new RB.CommentEditor({
                    canEdit: true,
                    reviewRequest: reviewRequest
                });
                expect(editor.get('canEdit')).toBe(true);
            });
        });

        describe('openIssue', function() {
            it('When user preference is true', function() {
                RB.UserSession.instance.set('commentsOpenAnIssue', true);

                editor = new RB.CommentEditor({
                    reviewRequest: reviewRequest
                });
                expect(editor.get('openIssue')).toBe(true);
            });

            it('When user preference is false', function() {
                RB.UserSession.instance.set('commentsOpenAnIssue', false);

                editor = new RB.CommentEditor({
                    reviewRequest: reviewRequest
                });
                expect(editor.get('openIssue')).toBe(false);
            });

            it('With explicitly set value', function() {
                RB.UserSession.instance.set('commentsOpenAnIssue', false);

                editor = new RB.CommentEditor({
                    openIssue: true,
                    reviewRequest: reviewRequest
                });
                expect(editor.get('openIssue')).toBe(true);
            });

            it('When reloading the page with explicitly set value', function() {
                RB.UserSession.instance.set('commentsOpenAnIssue', true);

                comment = createComment();
                comment.set({
                    loaded: false,
                    issueOpened: false
                });

                editor = new RB.CommentEditor({
                    comment: comment,
                    reviewRequest: reviewRequest
                });
                expect(editor.get('openIssue')).toBe(false);
            });
        });

        describe('richText', function() {
            it('When user preference is true', function() {
                RB.UserSession.instance.set('defaultUseRichText', true);

                editor = new RB.CommentEditor({
                    reviewRequest: reviewRequest
                });
                expect(editor.get('richText')).toBe(true);
            });

            it('When user preference is false', function() {
                RB.UserSession.instance.set('defaultUseRichText', false);

                editor = new RB.CommentEditor({
                    reviewRequest: reviewRequest
                });
                expect(editor.get('richText')).toBe(false);
            });

            it('With explicitly set value', function() {
                RB.UserSession.instance.set('defaultUseRichText', false);

                editor = new RB.CommentEditor({
                    richText: true,
                    reviewRequest: reviewRequest
                });
                expect(editor.get('richText')).toBe(true);
            });
        });
    });

    describe('Loading comment', function() {
        describe('With comment richText=true', function() {
            var comment;

            beforeEach(function() {
                comment = createComment();

                comment.set({
                    id: 123,
                    loaded: true,
                    richText: true,
                    text: '<p>this _is_ a <em>test</em></p>',
                    rawTextFields: {
                        text: 'this \\_is\\_ a _test_'
                    },
                    markdownTextFields: {
                        text: 'this \\_is\\_ a _test_'
                    }
                });
            });

            it('When defaultUseRichText=true', function() {
                RB.UserSession.instance.set('defaultUseRichText', true);
                editor.set('comment', comment);
                editor.beginEdit();

                expect(editor.get('dirty')).toBe(false);
                expect(editor.get('richText')).toBe(true);
                expect(editor.get('text')).toBe('this \\_is\\_ a _test_');
            });

            it('When defaultUseRichText=false', function() {
                RB.UserSession.instance.set('defaultUseRichText', false);
                editor.set('comment', comment);
                editor.beginEdit();

                expect(editor.get('dirty')).toBe(false);
                expect(editor.get('richText')).toBe(true);
                expect(editor.get('text')).toBe('this \\_is\\_ a _test_');
            });
        });

        describe('With comment richText=false', function() {
            var comment;

            beforeEach(function() {
                comment = createComment();

                comment.set({
                    id: 123,
                    loaded: true,
                    richText: false,
                    text: '<p>this _is_ a test</p>',
                    rawTextFields: {
                        text: 'this _is_ a _test_'
                    },
                    markdownTextFields: {
                        text: 'this \\_is\\_ a \\_test\\_'
                    }
                });
            });

            it('When defaultUseRichText=true', function() {
                RB.UserSession.instance.set('defaultUseRichText', true);
                editor.set('comment', comment);
                editor.beginEdit();

                expect(editor.get('dirty')).toBe(false);
                expect(editor.get('richText')).toBe(true);
                expect(editor.get('text')).toBe('this \\_is\\_ a \\_test\\_');
            });

            it('When defaultUseRichText=false', function() {
                RB.UserSession.instance.set('defaultUseRichText', false);
                editor.set('comment', comment);
                editor.beginEdit();

                expect(editor.get('dirty')).toBe(false);
                expect(editor.get('richText')).toBe(false);
                expect(editor.get('text')).toBe('this _is_ a _test_');
            });
        });
    });

    describe('Capability states', function() {
        describe('canDelete', function() {
            it('When not editing', function() {
                expect(editor.get('editing')).toBe(false);
                expect(editor.get('canDelete')).toBe(false);
            });

            it('When editing new comment', function() {
                editor.set('comment', createComment());

                editor.beginEdit();
                expect(editor.get('canDelete')).toBe(false);
            });

            it('When editing existing comment', function() {
                var comment = createComment();
                comment.set({
                    id: 123,
                    loaded: true
                });
                editor.set('comment', comment);

                editor.beginEdit();
                expect(editor.get('canDelete')).toBe(true);
            });

            it('When editing existing comment with canEdit=false', function() {
                var comment = createComment();
                comment.set({
                    id: 123,
                    loaded: true
                });

                editor.set({
                    canEdit: false,
                    comment: comment
                });

                expect(function() { editor.beginEdit(); }).toThrow();
                expect(console.assert).toHaveBeenCalled();
                expect(editor.get('canDelete')).toBe(false);
            });
        });

        describe('canSave', function() {
            it('When not editing', function() {
                expect(editor.get('editing')).toBe(false);
                expect(editor.get('canSave')).toBe(false);
            });

            it('When editing comment with text', function() {
                var comment = createComment();
                editor.set('comment', comment);
                editor.beginEdit();
                editor.set('text', 'Foo');
                expect(editor.get('canSave')).toBe(true);
            });

            it('When editing comment with initial state', function() {
                var comment = createComment();
                editor.set('comment', comment);
                editor.beginEdit();
                expect(editor.get('canSave')).toBe(false);
            });

            it('When editing comment without text', function() {
                var comment = createComment();
                editor.set('comment', comment);
                editor.beginEdit();
                editor.set('text', '');
                expect(editor.get('canSave')).toBe(false);
            });
        });
    });

    describe('States', function() {
        describe('dirty', function() {
            it('Initial state', function() {
                expect(editor.get('dirty')).toBe(false);
            });

            it('After new comment', function() {
                var comment = createComment();
                editor.set('dirty', true);
                editor.set('comment', comment);

                expect(editor.get('dirty')).toBe(false);
            });

            it('After text change', function() {
                editor.set('comment', createComment());
                editor.beginEdit();
                editor.set('text', 'abc');
                expect(editor.get('dirty')).toBe(true);
            });

            it('After toggling Open Issue', function() {
                editor.set('comment', createComment());
                editor.beginEdit();
                editor.set('openIssue', 'true');
                expect(editor.get('dirty')).toBe(true);
            });

            it('After saving', function() {
                var comment = createComment();
                editor.set('comment', comment);

                editor.beginEdit();
                editor.set('text', 'abc');
                expect(editor.get('dirty')).toBe(true);

                spyOn(comment, 'save').andCallFake(
                    function(callbacks, context) {
                        callbacks.success.call(context);
                    }
                );

                editor.save();
                expect(editor.get('dirty')).toBe(false);
            });

            it('After deleting', function() {
                var comment = createComment();
                comment.set({
                    id: 123,
                    loaded: true
                });
                editor.set('comment', comment);

                editor.beginEdit();
                editor.set('text', 'abc');
                expect(editor.get('dirty')).toBe(true);

                spyOn(comment, 'destroy').andCallFake(
                    function(callbacks, context) {
                        if (callbacks && callbacks.success) {
                            callbacks.success.call(context);
                        }
                    }
                );
                editor.deleteComment();
                expect(editor.get('dirty')).toBe(false);
            });
        });
    });

    describe('Operations', function() {
        it('setExtraData', function() {
            editor.setExtraData('key1', 'strvalue');
            editor.setExtraData('key2', 42);

            expect(editor.get('extraData')).toEqual({
                key1: 'strvalue',
                key2: 42
            });
        });

        it('getExtraData', function() {
            editor.set('extraData', {
                mykey: 'value'
            });

            expect(editor.getExtraData('mykey')).toBe('value');
        });

        describe('beginEdit', function() {
            it('With canEdit=true', function() {
                editor.set({
                    comment: createComment(),
                    canEdit: true
                });

                editor.beginEdit();
                expect(console.assert.calls[0].args[0]).toBeTruthy();
            });

            it('With canEdit=false', function() {
                editor.set({
                    comment: createComment(),
                    canEdit: false
                });

                expect(function() { editor.beginEdit(); }).toThrow();
                expect(console.assert.calls[0].args[0]).toBeFalsy();
            });

            it('With no comment', function() {
                expect(function() { editor.beginEdit(); }).toThrow();
                expect(console.assert.calls[0].args[0]).toBeTruthy();
                expect(console.assert.calls[1].args[0]).toBeFalsy();
            });
        });

        describe('cancel', function() {
            beforeEach(function() {
                spyOn(editor, 'close');
                spyOn(editor, 'trigger');
            });

            it('With comment', function() {
                var comment = createComment();
                spyOn(comment, 'destroyIfEmpty');
                editor.set('comment', comment);

                editor.cancel();
                expect(comment.destroyIfEmpty).toHaveBeenCalled();
                expect(editor.trigger).toHaveBeenCalledWith('canceled');
                expect(editor.close).toHaveBeenCalled();
            });

            it('Without comment', function() {
                editor.cancel();
                expect(editor.trigger).not.toHaveBeenCalledWith('canceled');
                expect(editor.close).toHaveBeenCalled();
            });
        });

        describe('destroy', function() {
            var comment;

            beforeEach(function() {
                comment = createComment();

                spyOn(comment, 'destroy').andCallFake(
                    function(callbacks, context) {
                        if (callbacks && callbacks.success) {
                            callbacks.success.call(context);
                        }
                    }
                );

                spyOn(editor, 'close');
                spyOn(editor, 'trigger');
            });

            it('With canDelete=false', function() {
                /* Set these in order, to override canDelete. */
                editor.set('comment', comment);
                editor.set('canDelete', false);

                expect(function() { editor.deleteComment(); }).toThrow();
                expect(console.assert.calls[0].args[0]).toBeFalsy();
                expect(comment.destroy).not.toHaveBeenCalled();
                expect(editor.trigger).not.toHaveBeenCalledWith('deleted');
                expect(editor.close).not.toHaveBeenCalled();
            });

            it('With canDelete=true', function() {
                /* Set these in order, to override canDelete. */
                editor.set('comment', comment);
                editor.set('canDelete', true);

                editor.deleteComment();
                expect(console.assert.calls[0].args[0]).toBeTruthy();
                expect(comment.destroy).toHaveBeenCalled();
                expect(editor.trigger).toHaveBeenCalledWith('deleted');
                expect(editor.close).toHaveBeenCalled();
            });
        });

        describe('save', function() {
            var comment;

            beforeEach(function() {
                comment = createComment();
                spyOn(comment, 'save').andCallFake(function(options) {
                    if (options && options.success) {
                        options.success();
                    }
                });

                spyOn(editor, 'trigger');
            });

            it('With canSave=false', function() {
                /* Set these in order, to override canSave. */
                editor.set('comment', comment);
                editor.set('canSave', false);

                expect(function() { editor.save(); }).toThrow();
                expect(console.assert.calls[0].args[0]).toBeFalsy();
                expect(comment.save).not.toHaveBeenCalled();
                expect(editor.trigger).not.toHaveBeenCalledWith('saved');
            });

            it('With canSave=true', function() {
                /* Set these in order, to override canSave. */
                var text = 'My text',
                    issue_opened = true;

                comment.set('issueOpened', false);
                editor.set('comment', comment);
                editor.set({
                    text: text,
                    issue_opened: issue_opened,
                    canSave: true,
                    richText: true
                });
                editor.setExtraData('mykey', 'myvalue');

                editor.save();
                expect(console.assert.calls[0].args[0]).toBeTruthy();
                expect(comment.save).toHaveBeenCalled();
                expect(comment.get('text')).toBe(text);
                expect(comment.get('issueOpened')).toBe(issue_opened);
                expect(comment.get('richText')).toBe(true);
                expect(comment.get('extraData')).toEqual({mykey: 'myvalue'});
                expect(editor.get('dirty')).toBe(false);
                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });
        });
    });
});
