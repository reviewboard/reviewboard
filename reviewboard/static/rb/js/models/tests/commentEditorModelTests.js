describe('models/CommentEditor', function() {
    var editor;

    beforeEach(function() {
        editor = new RB.CommentEditor({
            canEdit: true
        });
    });

    describe('Capability states', function() {
        describe('canDelete', function() {
            it('When not editing', function() {
                expect(editor.get('editing')).toBe(false);
                expect(editor.get('canDelete')).toBe(false);
            });

            it('When editing new comment', function() {
                editor.set('comment', new RB.DiffComment());

                editor.beginEdit();
                expect(editor.get('canDelete')).toBe(false);
            });

            it('When editing existing comment', function() {
                var comment = new RB.DiffComment();
                comment.loaded = true;

                editor.set('comment', comment);

                editor.beginEdit();
                expect(editor.get('canDelete')).toBe(true);
            });

            it('When editing existing comment with canEdit=false', function() {
                var comment = new RB.DiffComment();
                comment.loaded = true;

                editor.set({
                    canEdit: false,
                    comment: comment
                });

                expect(function() { editor.beginEdit() }).toThrow();
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
                editor.set('comment', new RB.DiffComment());
                editor.beginEdit();
                editor.set('text', 'Foo');
                expect(editor.get('canSave')).toBe(true);
            });

            it('When editing comment with initial state', function() {
                editor.set('comment', new RB.DiffComment());
                editor.beginEdit();
                expect(editor.get('canSave')).toBe(false);
            });

            it('When editing comment without text', function() {
                editor.set('comment', new RB.DiffComment());
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
                editor.set('dirty', true);
                editor.set('comment', new RB.DiffComment());

                expect(editor.get('dirty')).toBe(false);
            });

            it('After text change', function() {
                editor.set('comment', new RB.DiffComment());
                editor.beginEdit();
                editor.set('text', 'abc');
                expect(editor.get('dirty')).toBe(true);
            });

            it('After toggling Open Issue', function() {
                editor.set('comment', new RB.DiffComment());
                editor.beginEdit();
                editor.set('openIssue', 'true');
                expect(editor.get('dirty')).toBe(true);
            });

            it('After saving', function() {
                var comment = new RB.DiffComment();
                editor.set('comment', comment);

                editor.beginEdit();
                editor.set('text', 'abc');
                expect(editor.get('dirty')).toBe(true);

                spyOn(comment, 'save');
                editor.save();
                expect(editor.get('dirty')).toBe(false);
            });

            it('After deleting', function() {
                var comment = new RB.DiffComment();
                comment.loaded = true;
                editor.set('comment', comment);

                editor.beginEdit();
                editor.set('text', 'abc');
                expect(editor.get('dirty')).toBe(true);

                spyOn(comment, 'deleteComment');
                editor.deleteComment();
                expect(editor.get('dirty')).toBe(false);
            });
        });
    });

    describe('Operations', function() {
        describe('beginEdit', function() {
            it('With canEdit=true', function() {
                editor.set({
                    comment: new RB.DiffComment(),
                    canEdit: true
                });

                editor.beginEdit();
                expect(console.assert.calls[0].args[0]).toBeTruthy();
            });

            it('With canEdit=false', function() {
                editor.set({
                    comment: new RB.DiffComment(),
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
                var comment = new RB.DiffComment();
                spyOn(comment, 'deleteIfEmpty');
                editor.set('comment', comment);

                editor.cancel();
                expect(comment.deleteIfEmpty).toHaveBeenCalled();
                expect(editor.trigger).toHaveBeenCalledWith('canceled');
                expect(editor.close).toHaveBeenCalled();
            });

            it('Without comment', function() {
                editor.cancel();
                expect(editor.trigger).not.toHaveBeenCalledWith('canceled');
                expect(editor.close).toHaveBeenCalled();
            });
        });

        describe('deleteComment', function() {
            var comment;

            beforeEach(function() {
                comment = new RB.DiffComment();
                spyOn(comment, 'deleteComment');
                spyOn(editor, 'close');
                spyOn(editor, 'trigger');
            });

            it('With canDelete=false', function() {
                /* Set these in order, to override canDelete. */
                editor.set('comment', comment);
                editor.set('canDelete', false);

                expect(function() { editor.deleteComment(); }).toThrow();
                expect(console.assert.calls[0].args[0]).toBeFalsy();
                expect(comment.deleteComment).not.toHaveBeenCalled();
                expect(editor.trigger).not.toHaveBeenCalledWith('deleted');
                expect(editor.close).not.toHaveBeenCalled();
            });

            it('With canDelete=true', function() {
                /* Set these in order, to override canDelete. */
                editor.set('comment', comment);
                editor.set('canDelete', true);

                editor.deleteComment();
                expect(console.assert.calls[0].args[0]).toBeTruthy();
                expect(comment.deleteComment).toHaveBeenCalled();
                expect(editor.trigger).toHaveBeenCalledWith('deleted');
                expect(editor.close).toHaveBeenCalled();
            });
        });

        describe('save', function() {
            var comment;

            beforeEach(function() {
                comment = new RB.DiffComment();
                spyOn(comment, 'save');
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

                comment.issue_opened = false;
                editor.set('comment', comment);
                editor.set({
                    text: text,
                    issue_opened: issue_opened,
                    canSave: true
                });

                editor.save();
                expect(console.assert.calls[0].args[0]).toBeTruthy();
                expect(comment.save).toHaveBeenCalled();
                expect(comment.text).toBe(text);
                expect(comment.issue_opened).toBe(issue_opened);
                expect(editor.get('dirty')).toBe(false);
                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });
        });
    });
});
