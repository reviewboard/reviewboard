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

        describe('setDraftField', function() {
            var callbacks,
                draft;

            beforeEach(function() {
                callbacks = {
                    error: function() {},
                    success: function() {}
                };

                spyOn(callbacks, 'error');
                spyOn(callbacks, 'success');

                draft = editor.get('reviewRequest').draft;
            });

            describe('When publishing', function() {
                beforeEach(function() {
                    spyOn(editor, 'publishDraft');

                    editor.set({
                        publishing: true,
                        pendingSaveCount: 1
                    });
                });

                it('Successful saves', function() {
                    spyOn(draft, 'save')
                        .andCallFake(function(options, context) {
                            options.success.call(context);
                        });
                    editor.setDraftField('summary', 'My Summary', callbacks);

                    expect(callbacks.success).toHaveBeenCalled();
                    expect(editor.get('publishing')).toBe(false);
                    expect(editor.get('pendingSaveCount')).toBe(0);
                    expect(editor.publishDraft).toHaveBeenCalled();
                });

                it('Field set errors', function() {
                    spyOn(draft, 'save')
                        .andCallFake(function(options, context) {
                            options.error.call(context, draft, {
                                errorPayload: {
                                    fields: {
                                        summary: ['Something went wrong']
                                    }
                                }
                            });
                        });
                    editor.setDraftField('summary', 'My Summary', callbacks);

                    expect(callbacks.error).toHaveBeenCalled();
                    expect(editor.get('publishing')).toBe(false);
                    expect(editor.get('pendingSaveCount')).toBe(1);
                    expect(editor.publishDraft).not.toHaveBeenCalled();
                });
            });

            describe('Special fields', function() {
                describe('changeDescription', function() {
                    it('Discarded description', function() {
                        spyOn(reviewRequest, 'close')
                            .andCallFake(function(options) {
                                expect(options.type).toBe(
                                    RB.ReviewRequest.CLOSE_DISCARDED);
                                expect(options.description)
                                    .toBe('My description');
                            });

                        editor.setDraftField('changeDescription',
                                             'My description', {
                            closeType: RB.ReviewRequest.CLOSE_DISCARDED
                        });

                        expect(reviewRequest.close).toHaveBeenCalled();
                    });

                    it('Draft description', function() {
                        spyOn(reviewRequest, 'close');
                        spyOn(reviewRequest.draft, 'save');

                        editor.setDraftField('changeDescription',
                                             'My description');

                        expect(reviewRequest.close).not.toHaveBeenCalled();
                        expect(reviewRequest.draft.save).toHaveBeenCalled();
                    });

                    it('Submitted description', function() {
                        spyOn(reviewRequest, 'close')
                            .andCallFake(function(options) {
                                expect(options.type).toBe(
                                    RB.ReviewRequest.CLOSE_SUBMITTED);
                                expect(options.description)
                                    .toBe('My description');
                            });

                        editor.setDraftField('changeDescription',
                                             'My description', {
                            closeType: RB.ReviewRequest.CLOSE_SUBMITTED
                        });

                        expect(reviewRequest.close).toHaveBeenCalled();
                    });
                });

                describe('targetGroups', function() {
                    it('Empty', function() {
                        spyOn(draft, 'save')
                            .andCallFake(function(options, context) {
                                options.success.call(context);
                            });

                        editor.setDraftField('targetGroups', '', callbacks);

                        expect(callbacks.success).toHaveBeenCalled();
                    });

                    it('With values', function() {
                        spyOn(draft, 'save')
                            .andCallFake(function(options, context) {
                                options.success.call(context);
                            });

                        editor.setDraftField('targetGroups', 'group1, group2',
                                             callbacks);

                        expect(callbacks.success).toHaveBeenCalled();
                    });

                    it('With invalid groups', function() {
                        spyOn(draft, 'save')
                            .andCallFake(function(options, context) {
                                options.error.call(context, draft, {
                                    errorPayload: {
                                        fields: {
                                            target_groups: ['group1', 'group2']
                                        }
                                    }
                                });
                            });

                        editor.setDraftField('targetGroups', 'group1, group2',
                                             callbacks);

                        expect(callbacks.error).toHaveBeenCalledWith({
                            errorText: "Groups 'group1' and 'group2' do " +
                                       "not exist."
                        });
                    });
                });

                describe('targetPeople', function() {
                    it('Empty', function() {
                        spyOn(draft, 'save')
                            .andCallFake(function(options, context) {
                                options.success.call(context);
                            });

                        editor.setDraftField('targetPeople', '', callbacks);

                        expect(callbacks.success).toHaveBeenCalled();
                    });

                    it('With values', function() {
                        spyOn(draft, 'save')
                            .andCallFake(function(options, context) {
                                options.success.call(context);
                            });

                        editor.setDraftField('targetPeople', 'user1, user2',
                                             callbacks);

                        expect(callbacks.success).toHaveBeenCalled();
                    });

                    it('With invalid users', function() {
                        spyOn(draft, 'save')
                            .andCallFake(function(options, context) {
                                options.error.call(context, draft, {
                                    errorPayload: {
                                        fields: {
                                            target_people: ['user1', 'user2']
                                        }
                                    }
                                });
                            });

                        editor.setDraftField('targetPeople', 'user1, user2',
                                             callbacks);

                        expect(callbacks.error).toHaveBeenCalledWith({
                            errorText: "Users 'user1' and 'user2' do not exist."
                        });
                    });
                });
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
