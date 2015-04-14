suite('rb/models/ReviewRequestEditor', function() {
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
                var fileAttachments = editor.get('fileAttachments'),
                    fileAttachment;

                expect(fileAttachments.length).toBe(0);
                fileAttachment = editor.createFileAttachment();
                expect(fileAttachments.length).toBe(1);

                expect(fileAttachments.at(0)).toBe(fileAttachment);
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

        describe('getDraftField', function() {
            var value;

            it('For closeDescription', function() {
                reviewRequest.set('closeDescription', 'Test');

                value = editor.getDraftField('closeDescription', {});
                expect(value).toBe('Test');
            });

            it('For closeDescriptionRichText', function() {
                reviewRequest.set('closeDescriptionRichText', true);

                value = editor.getDraftField('closeDescriptionRichText', {});
                expect(value).toBe(true);
            });

            it('For draft fields', function() {
                reviewRequest.draft.set('description', 'Test');

                value = editor.getDraftField('description', {});
                expect(value).toBe('Test');
            });

            it('For custom fields', function() {
                reviewRequest.draft.get('extraData').foo = 'Test';

                value = editor.getDraftField('bar', {
                    useExtraData: true,
                    fieldID: 'foo'
                });
                expect(value).toBe('Test');
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
                    editor.setDraftField('summary', 'My Summary', _.defaults({
                        jsonFieldName: 'summary'
                    }, callbacks));

                    expect(callbacks.error).toHaveBeenCalled();
                    expect(editor.get('publishing')).toBe(false);
                    expect(editor.get('pendingSaveCount')).toBe(1);
                    expect(editor.publishDraft).not.toHaveBeenCalled();
                });
            });

            describe('Rich text fields', function() {
                describe('changeDescription', function() {
                    describe('Draft description', function() {
                        function testDraftDescription(richText, textType) {
                            spyOn(reviewRequest, 'close');
                            spyOn(reviewRequest.draft, 'save');

                            editor.setDraftField(
                                'changeDescription',
                                'My description',
                                {
                                    allowMarkdown: true,
                                    fieldID: 'changedescription',
                                    richText: richText,
                                    jsonFieldName: 'changedescription',
                                    jsonTextTypeFieldName:
                                        'changedescription_text_type'
                                });

                            expect(reviewRequest.close)
                                .not.toHaveBeenCalled();
                            expect(reviewRequest.draft.save)
                                .toHaveBeenCalled();

                            expect(
                                reviewRequest.draft.save.calls[0].args[0].data
                            ).toEqual({
                                changedescription_text_type: textType,
                                changedescription: 'My description',
                                force_text_type: 'html',
                                include_text_types: 'raw'
                            });
                        }

                        it('For Markdown', function() {
                            testDraftDescription(true, 'markdown');
                        });

                        it('For plain text', function() {
                            testDraftDescription(false, 'plain');
                        });
                    });
                });

                describe('closeDescription', function() {
                    function testCloseDescription(closeType, richText) {
                        spyOn(reviewRequest, 'close')
                            .andCallFake(function(options) {
                                expect(options.type).toBe(closeType);
                                expect(options.description)
                                    .toBe('My description');
                                expect(options.richText).toBe(richText);
                            });

                        editor.setDraftField('closeDescription',
                                             'My description', {
                            closeType: closeType,
                            richText: richText
                        });

                        expect(reviewRequest.close).toHaveBeenCalled();
                    }

                    describe('Discarded description', function() {
                        it('For Markdown', function() {
                            testCloseDescription(
                                RB.ReviewRequest.CLOSE_DISCARDED,
                                true,
                                'markdown');
                        });

                        it('For plain text', function() {
                            testCloseDescription(
                                RB.ReviewRequest.CLOSE_DISCARDED,
                                false,
                                'plain');
                        });
                    });

                    describe('Submitted description', function() {
                        it('For Markdown', function() {
                            testCloseDescription(
                                RB.ReviewRequest.CLOSE_SUBMITTED,
                                true,
                                'markdown');
                        });

                        it('For plain text', function() {
                            testCloseDescription(
                                RB.ReviewRequest.CLOSE_SUBMITTED,
                                false,
                                'plain');
                        });
                    });
                });
            });

            describe('Special list fields', function() {
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
                                             _.defaults({
                            jsonFieldName: 'target_groups'
                        }, callbacks));

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

                        editor.setDraftField('targetPeople', '', _.defaults({
                            jsonFieldName: 'target_people'
                        }, callbacks));

                        expect(callbacks.success).toHaveBeenCalled();
                    });

                    it('With values', function() {
                        spyOn(draft, 'save')
                            .andCallFake(function(options, context) {
                                options.success.call(context);
                            });

                        editor.setDraftField(
                            'targetPeople', 'user1, user2',
                            _.defaults({
                                jsonFieldName: 'target_people'
                            }, callbacks));

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

                        editor.setDraftField(
                            'targetPeople', 'user1, user2',
                            _.defaults({
                                jsonFieldName: 'target_people'
                            }, callbacks));

                        expect(callbacks.error).toHaveBeenCalledWith({
                            errorText: "Users 'user1' and 'user2' do not exist."
                        });
                    });
                });
            });

            describe('Custom fields', function() {
                describe('Rich text fields', function() {
                    function testFields(richText, textType) {
                        spyOn(reviewRequest.draft, 'save');

                        editor.setDraftField(
                            'myField',
                            'Test text.',
                            {
                                allowMarkdown: true,
                                useExtraData: true,
                                fieldID: 'myfield',
                                richText: richText,
                                jsonFieldName: 'myfield',
                                jsonTextTypeFieldName:
                                    'myfield_text_type'
                            });

                        expect(reviewRequest.draft.save)
                            .toHaveBeenCalled();
                        expect(
                            reviewRequest.draft.save.calls[0].args[0].data
                        ).toEqual({
                            'extra_data.myfield_text_type': textType,
                            'extra_data.myfield': 'Test text.',
                            force_text_type: 'html',
                            include_text_types: 'raw'
                        });
                    }

                    it('For Markdown', function() {
                        testFields(true, 'markdown');
                    });

                    it('For plain text', function() {
                        testFields(false, 'plain');
                    });
                });
            });
        });
    });

    describe('Reviewed objects', function() {
        describe('File attachments', function() {
            it('Removed when destroyed', function() {
                var fileAttachments = editor.get('fileAttachments'),
                    fileAttachment = editor.createFileAttachment(),
                    draft = editor.get('reviewRequest').draft;

                spyOn(draft, 'ensureCreated')
                    .andCallFake(function(options, context) {
                        options.success.call(context);
                    });

                expect(fileAttachments.at(0)).toBe(fileAttachment);

                fileAttachment.destroy();

                expect(fileAttachments.length).toBe(0);
            });
        });

        describe('Screenshots', function() {
            it('Removed when destroyed', function() {
                var screenshots = editor.get('screenshots'),
                    screenshot = reviewRequest.createScreenshot();

                screenshots.add(screenshot);
                expect(screenshots.at(0)).toBe(screenshot);

                screenshot.destroy();

                expect(screenshots.length).toBe(0);
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
                var fileAttachment = editor.createFileAttachment(),
                    draft = editor.get('reviewRequest').draft;

                spyOn(draft, 'ensureCreated')
                    .andCallFake(function(options, context) {
                        options.success.call(context);
                    });

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
