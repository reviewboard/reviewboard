describe('models/ReviewRequestEditor', function() {
    var reviewRequest,
        editor;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest({
            id: 1
        });

        editor = new RB.ReviewRequestEditor({
            reviewRequest: reviewRequest
        });
    });

    describe('Methods', function() {
        describe('createFileAttachment', function() {
            it('With new FileAttachment', function() {
                var fileAttachment;

                expect(editor.fileAttachments.length).toBe(0);
                fileAttachment = editor.createFileAttachment();
                expect(editor.fileAttachments.length).toBe(1);

                expect(editor.fileAttachments.at(0)).toBe(fileAttachment);
            });
        });

        describe('decr', function() {
            it('With integer attribute', function() {
                editor.set('myint', 1);

                editor.decr('myint');
                expect(editor.get('myint')).toBe(0);
            });

            it('With non-integer attribute', function() {
                editor.set('foo', 'abc');

                expect(function() { editor.decr('foo'); }).toThrow();

                expect(console.assert).toHaveBeenCalled();
                expect(console.assert.mostRecentCall.args[0]).toBe(false);
                expect(editor.get('foo')).toBe('abc');
            });

            describe('editCount', function() {
                it('When > 0', function() {
                    editor.set('editCount', 1);

                    editor.decr('editCount');
                    expect(editor.get('editCount')).toBe(0);
                    expect(editor.validationError).toBe(null);
                });

                it('When 0', function() {
                    editor.set('editCount', 0);

                    editor.decr('editCount');
                    expect(editor.get('editCount')).toBe(0);
                    expect(editor.validationError).toBe(
                        RB.ReviewRequestEditor.strings.UNBALANCED_EDIT_COUNT);
                });
            });
        });

        describe('incr', function() {
            it('With integer attribute', function() {
                editor.set('myint', 0);
                editor.incr('myint');
                expect(editor.get('myint')).toBe(1);
            });

            it('With non-integer attribute', function() {
                editor.set('foo', 'abc');

                expect(function() { editor.incr('foo'); }).toThrow();

                expect(console.assert).toHaveBeenCalled();
                expect(console.assert.mostRecentCall.args[0]).toBe(false);
                expect(editor.get('foo')).toBe('abc');
            });
        });
    });

    describe('Reviewed objects', function() {
        describe('File attachments', function() {
            it('Removed when destroyed', function() {
                var fileAttachment = editor.createFileAttachment();

                expect(editor.fileAttachments.at(0)).toBe(fileAttachment);

                fileAttachment.destroy();

                expect(editor.fileAttachments.length).toBe(0);
            });
        });

        describe('Screenshots', function() {
            it('Removed when destroyed', function() {
                var screenshot = reviewRequest.createScreenshot();

                editor.screenshots.add(screenshot);
                expect(editor.screenshots.at(0)).toBe(screenshot);

                screenshot.destroy();

                expect(editor.screenshots.length).toBe(0);
            });
        });
    });

    describe('Events', function() {
        describe('saved', function() {
            it('When file attachment saved', function() {
                var fileAttachment = editor.createFileAttachment();

                spyOn(editor, 'trigger');
                fileAttachment.trigger('saved');

                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });

            it('When file attachment destroyed', function() {
                var fileAttachment = editor.createFileAttachment();

                spyOn(editor, 'trigger');
                fileAttachment.destroy();

                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });
        });

        describe('saving', function() {
            it('When file attachment saving', function() {
                var fileAttachment = editor.createFileAttachment();

                spyOn(editor, 'trigger');
                fileAttachment.trigger('saving');

                expect(editor.trigger).toHaveBeenCalledWith('saving');
            });
        });
    });
});
