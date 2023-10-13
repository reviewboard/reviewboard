import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    expectAsync,
    it,
    spyOn,
} from 'jasmine-core';

import { ReviewRequestEditor } from 'reviewboard/reviews';


suite('rb/models/ReviewRequestEditor', function() {
    let reviewRequest;
    let editor;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest({
            id: 1,
        });

        editor = new ReviewRequestEditor({
            reviewRequest: reviewRequest,
        });
    });

    describe('Methods', function() {
        describe('createFileAttachment', function() {
            it('With new FileAttachment', function() {
                const fileAttachments = editor.get('fileAttachments');

                expect(fileAttachments.length).toBe(0);

                const fileAttachment = editor.createFileAttachment();
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

                expect(() => editor.decr('foo')).toThrow();

                expect(console.assert).toHaveBeenCalled();
                expect(console.assert.calls.mostRecent().args[0]).toBe(false);
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
                        ReviewRequestEditor.strings.UNBALANCED_EDIT_COUNT);
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

                expect(() => editor.incr('foo')).toThrow();

                expect(console.assert).toHaveBeenCalled();
                expect(console.assert.calls.mostRecent().args[0]).toBe(false);
                expect(editor.get('foo')).toBe('abc');
            });
        });

        describe('getDraftField', function() {
            it('For closeDescription', function() {
                reviewRequest.set('closeDescription', 'Test');

                const value = editor.getDraftField('closeDescription');
                expect(value).toBe('Test');
            });

            it('For closeDescriptionRichText', function() {
                reviewRequest.set('closeDescriptionRichText', true);

                const value = editor.getDraftField('closeDescriptionRichText');
                expect(value).toBe(true);
            });

            it('For draft fields', function() {
                reviewRequest.draft.set('description', 'Test');

                const value = editor.getDraftField('description');
                expect(value).toBe('Test');
            });

            it('With useExtraData', function() {
                const extraData = reviewRequest.draft.get('extraData');

                extraData.foo = '**Test**';

                const value = editor.getDraftField('foo', {
                    useExtraData: true,
                });
                expect(value).toBe('**Test**');
            });

            describe('With useExtraData and useRawTextValue', function() {
                it('With field in rawTextFields', function() {
                    const draft = reviewRequest.draft;
                    const extraData = reviewRequest.draft.get('extraData');

                    extraData.foo = '<b>Test</b>';
                    draft.set('rawTextFields', {
                        extra_data: {
                            foo: '**Test**',
                        },
                    });

                    const value = editor.getDraftField('foo', {
                        useExtraData: true,
                        useRawTextValue: true,
                    });
                    expect(value).toBe('**Test**');
                });

                it('With field not in rawTextFields', function() {
                    const extraData = reviewRequest.draft.get('extraData');

                    extraData.foo = '<b>Test</b>';

                    const value = editor.getDraftField('foo', {
                        useExtraData: true,
                        useRawTextValue: true,
                    });
                    expect(value).toBe('<b>Test</b>');
                });
            });
        });

        describe('setDraftField', function() {
            let draft;

            beforeEach(function() {
                draft = editor.get('reviewRequest').draft;
            });

            describe('Rich text fields', function() {
                describe('changeDescription', function() {
                    describe('Draft description', function() {
                        async function testDraftDescription(richText, textType) {
                            spyOn(reviewRequest, 'close');
                            spyOn(reviewRequest.draft, 'save').and.resolveTo();

                            await editor.setDraftField(
                                'changeDescription',
                                'My description',
                                {
                                    allowMarkdown: true,
                                    fieldID: 'changedescription',
                                    jsonFieldName: 'changedescription',
                                    jsonTextTypeFieldName:
                                        'changedescription_text_type',
                                    richText: richText,
                                });

                            expect(reviewRequest.close).not.toHaveBeenCalled();
                            expect(reviewRequest.draft.save).toHaveBeenCalled();
                            expect(
                                reviewRequest.draft.save.calls.argsFor(0)[0].data
                            ).toEqual({
                                changedescription: 'My description',
                                changedescription_text_type: textType,
                                force_text_type: 'html',
                                include_text_types: 'raw',
                            });
                        }

                        it('For Markdown', async function() {
                            await testDraftDescription(true, 'markdown');
                        });

                        it('For plain text', async function() {
                            await testDraftDescription(false, 'plain');
                        });
                    });
                });
            });

            describe('Special list fields', function() {
                describe('targetGroups', function() {
                    it('Empty', async function() {
                        spyOn(draft, 'save').and.resolveTo();

                        await editor.setDraftField(
                            'targetGroups', '',
                            { jsonFieldName: 'target_groups' });

                        expect(draft.save).toHaveBeenCalled();
                    });

                    it('With values', async function() {
                        spyOn(draft, 'save').and.resolveTo();

                        await editor.setDraftField(
                            'targetGroups', 'group1, group2',
                            { jsonFieldName: 'target_groups' });

                        expect(draft.save).toHaveBeenCalled();
                    });

                    it('With invalid groups', async function() {
                        spyOn(draft, 'save').and.rejectWith(new BackboneError(
                            draft,
                            {
                                errorPayload: {
                                    fields: {
                                        target_groups: ['group1', 'group2'],
                                    },
                                },
                            },
                            {}));

                        await expectAsync(
                            editor.setDraftField(
                                'targetGroups', 'group1, group2',
                                { jsonFieldName: 'target_groups' }))
                            .toBeRejectedWith(Error(
                                'Groups "group1" and "group2" do not exist.'));
                    });
                });

                describe('targetPeople', function() {
                    it('Empty', async function() {
                        spyOn(draft, 'save').and.resolveTo();

                        await editor.setDraftField(
                            'targetPeople', '',
                            { jsonFieldName: 'target_people' });

                        expect(draft.save).toHaveBeenCalled();
                    });

                    it('With values', async function() {
                        spyOn(draft, 'save').and.resolveTo();

                        await editor.setDraftField(
                            'targetPeople', 'user1, user2',
                            { jsonFieldName: 'target_people' });

                        expect(draft.save).toHaveBeenCalled();
                    });

                    it('With invalid users', async function() {
                        spyOn(draft, 'save').and.rejectWith(new BackboneError(
                            draft,
                            {
                                errorPayload: {
                                    fields: {
                                        target_people: ['user1', 'user2'],
                                    },
                                },
                            },
                            {}));

                        await expectAsync(
                            editor.setDraftField(
                                'targetPeople', 'user1, user2',
                                { jsonFieldName: 'target_people' }))
                            .toBeRejectedWith(Error(
                                'Users "user1" and "user2" do not exist.'));
                    });
                });

                describe('submitter', function() {
                    it('Empty', async function() {
                        spyOn(draft, 'save').and.resolveTo();

                        await editor.setDraftField(
                            'submitter', '', { jsonFieldName: 'submitter' });

                        expect(draft.save).toHaveBeenCalled();
                    });

                    it('With value', async function() {
                        spyOn(draft, 'save').and.resolveTo();

                        await editor.setDraftField(
                            'submitter', 'user1',
                            { jsonFieldName: 'submitter' });

                        expect(draft.save).toHaveBeenCalled();
                    });

                    it('With invalid user', async function() {
                        spyOn(draft, 'save').and.rejectWith(new BackboneError(
                            draft,
                            {
                                errorPayload: {
                                    fields: {
                                        submitter: ['user1'],
                                    },
                                },
                            },
                            {}));

                        await expectAsync(
                            editor.setDraftField(
                                'submitter', 'user1',
                                { jsonFieldName: 'submitter' }))
                            .toBeRejectedWith(Error(
                                'User "user1" does not exist.'));
                    });
                });
            });

            describe('Custom fields', function() {
                describe('Rich text fields', function() {
                    async function testFields(richText, textType) {
                        spyOn(reviewRequest.draft, 'save').and.resolveTo();

                        await editor.setDraftField(
                            'myField',
                            'Test text.',
                            {
                                allowMarkdown: true,
                                fieldID: 'myfield',
                                jsonFieldName: 'myfield',
                                jsonTextTypeFieldName: 'myfield_text_type',
                                richText: richText,
                                useExtraData: true,
                            });

                        expect(reviewRequest.draft.save).toHaveBeenCalled();
                        expect(
                            reviewRequest.draft.save.calls.argsFor(0)[0].data
                        ).toEqual({
                            'extra_data.myfield': 'Test text.',
                            'extra_data.myfield_text_type': textType,
                            'force_text_type': 'html',
                            'include_text_types': 'raw',
                        });
                    }

                    it('For Markdown', async function() {
                        await testFields(true, 'markdown');
                    });

                    it('For plain text', async function() {
                        await testFields(false, 'plain');
                    });
                });
            });
        });
    });

    describe('Reviewed objects', function() {
        describe('File attachments', function() {
            it('Removed when destroyed', async function() {
                const fileAttachments = editor.get('fileAttachments');
                const fileAttachment = editor.createFileAttachment();
                const draft = editor.get('reviewRequest').draft;

                spyOn(draft, 'ensureCreated').and.resolveTo();

                expect(fileAttachments.at(0)).toBe(fileAttachment);

                await fileAttachment.destroy();
                expect(fileAttachments.length).toBe(0);
            });
        });

        describe('Screenshots', function() {
            it('Removed when destroyed', async function() {
                const screenshots = editor.get('screenshots');
                const screenshot = reviewRequest.createScreenshot();

                screenshots.add(screenshot);
                expect(screenshots.at(0)).toBe(screenshot);

                await screenshot.destroy();
                expect(screenshots.length).toBe(0);
            });
        });
    });

    describe('Events', function() {
        describe('saved', function() {
            it('When new file attachment saved', function() {
                const fileAttachment = editor.createFileAttachment();

                spyOn(editor, 'trigger');
                fileAttachment.trigger('saved');

                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });

            it('When new file attachment destroyed', async function() {
                const fileAttachment = editor.createFileAttachment();
                const draft = editor.get('reviewRequest').draft;

                spyOn(draft, 'ensureCreated').and.resolveTo();

                spyOn(editor, 'trigger');

                await fileAttachment.destroy();
                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });

            it('When existing file attachment saved', function() {
                const fileAttachment =
                    reviewRequest.draft.createFileAttachment();

                editor = new ReviewRequestEditor({
                    fileAttachments: new Backbone.Collection(
                        [fileAttachment]),
                    reviewRequest: reviewRequest,
                });

                spyOn(editor, 'trigger');
                fileAttachment.trigger('saved');

                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });

            it('When existing file attachment destroyed', async function() {
                const fileAttachment =
                    reviewRequest.draft.createFileAttachment();

                editor = new ReviewRequestEditor({
                    fileAttachments: new Backbone.Collection(
                        [fileAttachment]),
                    reviewRequest: reviewRequest,
                });

                spyOn(reviewRequest.draft, 'ensureCreated').and.resolveTo();

                spyOn(editor, 'trigger');

                await fileAttachment.destroy();
                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });

            it('When existing screenshot saved', function() {
                const screenshot = reviewRequest.createScreenshot();

                editor = new ReviewRequestEditor({
                    reviewRequest: reviewRequest,
                    screenshots: new Backbone.Collection([screenshot]),
                });

                spyOn(editor, 'trigger');
                screenshot.trigger('saved');

                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });

            it('When existing screenshot destroyed', async function() {
                const screenshot = reviewRequest.createScreenshot();

                editor = new ReviewRequestEditor({
                    reviewRequest: reviewRequest,
                    screenshots: new Backbone.Collection([screenshot]),
                });

                spyOn(reviewRequest.draft, 'ensureCreated').and.resolveTo();

                spyOn(editor, 'trigger');

                await screenshot.destroy();
                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });
        });

        describe('saving', function() {
            it('When new file attachment saving', function() {
                const fileAttachment = editor.createFileAttachment();

                spyOn(editor, 'trigger');
                fileAttachment.trigger('saving');

                expect(editor.trigger).toHaveBeenCalledWith('saving');
            });

            it('When existing file attachment saving', function() {
                const fileAttachment =
                    reviewRequest.draft.createFileAttachment();

                editor = new ReviewRequestEditor({
                    fileAttachments: new Backbone.Collection(
                        [fileAttachment]),
                    reviewRequest: reviewRequest,
                });

                spyOn(editor, 'trigger');
                fileAttachment.trigger('saving');

                expect(editor.trigger).toHaveBeenCalledWith('saving');
            });

            it('When screenshot saving', function() {
                const screenshot = reviewRequest.createScreenshot();

                editor = new ReviewRequestEditor({
                    reviewRequest: reviewRequest,
                    screenshots: new Backbone.Collection([screenshot]),
                });

                spyOn(editor, 'trigger');
                screenshot.trigger('saving');

                expect(editor.trigger).toHaveBeenCalledWith('saving');
            });
        });
    });
});
