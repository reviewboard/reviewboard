import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    ReviewRequestEditor,
    ReviewRequestEditorView,
    ReviewRequestFields,
} from 'reviewboard/reviews';


const {
    BaseFieldView,
    MultilineTextFieldView,
    TextFieldView,
} = ReviewRequestFields;


suite('rb/views/reviewRequestFieldViews', function() {
    let reviewRequest;
    let draft;
    let extraData;
    let rawTextFields;
    let editor;
    let editorView;
    let field;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest({
            id: 1,
        });

        draft = reviewRequest.draft;
        extraData = draft.get('extraData');

        rawTextFields = {
            extra_data: {},
        };
        draft.set('rawTextFields', rawTextFields);

        editor = new ReviewRequestEditor({
            reviewRequest: reviewRequest,
        });

        editorView = new ReviewRequestEditorView({
            model: editor,
        });

        spyOn(draft, 'save').and.resolveTo();
        spyOn(draft, 'ready').and.resolveTo();
    });

    describe('BaseFieldView', function() {
        beforeEach(function() {
            field = new BaseFieldView({
                fieldID: 'my_field',
                model: editor,
            });
        });

        describe('Initialization', function() {
            it('Default behavior', function() {
                expect(field.$el.data('field-id')).toBe('my_field');
                expect(field.jsonFieldName).toBe('my_field');
            });

            it('With custom jsonFieldName', function() {
                const field = new BaseFieldView({
                    fieldID: 'my_field',
                    jsonFieldName: 'my_custom_name',
                    model: editor,
                });

                expect(field.$el.data('field-id')).toBe('my_field');
                expect(field.jsonFieldName).toBe('my_custom_name');
            });
        });

        describe('Properties', function() {
            it('fieldName', function() {
                expect(field.fieldName()).toBe('myField');
            });
        });

        describe('Methods', function() {
            describe('_loadValue', function() {
                it('Built-in field', function() {
                    field.useExtraData = false;
                    draft.set('myField', 'this is a test');

                    expect(field._loadValue()).toBe('this is a test');
                });

                it('Custom field', function() {
                    extraData.my_field = 'this is a test';

                    expect(field._loadValue()).toBe('this is a test');
                });

                it('Custom field and custom jsonFieldName', function() {
                    const field = new BaseFieldView({
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    extraData.foo = 'this is a test';

                    expect(field._loadValue()).toBe('this is a test');
                });
            });

            describe('_saveValue', function() {
                it('Built-in field', function(done) {
                    field.useExtraData = false;
                    field._saveValue('test')
                        .then(() => {
                            expect(draft.save.calls.argsFor(0)[0].data)
                                .toEqual({
                                    my_field: 'test',
                                });

                            done();
                        })
                        .catch(err => done.fail(err));
                });

                it('Custom field', function(done) {
                    field._saveValue('this is a test')
                        .then(() => {
                            expect(draft.save.calls.argsFor(0)[0].data)
                                .toEqual({
                                    'extra_data.my_field': 'this is a test',
                                });

                            done();
                        })
                        .catch(err => done.fail(err));
                });

                it('Custom field and custom jsonFieldName', function(done) {
                    const field = new BaseFieldView({
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    field._saveValue('this is a test')
                        .then(() => {
                            expect(draft.save.calls.argsFor(0)[0].data)
                                .toEqual({
                                    'extra_data.foo': 'this is a test',
                                });

                            done();
                        })
                        .catch(err => done.fail(err));
                });
            });
        });
    });

    describe('TextFieldView', function() {
        beforeEach(function() {
            field = new TextFieldView({
                fieldID: 'my_field',
                model: editor,
            });
            editorView.addFieldView(field);
        });

        describe('Properties', function() {
            describe('jsonTextTypeFieldName', function() {
                it('With fieldID != "text"', function() {
                    expect(field.jsonTextTypeFieldName)
                        .toBe('my_field_text_type');
                });

                it('With fieldID = "text"', function() {
                    field = new TextFieldView({
                        fieldID: 'text',
                        model: editor,
                    });

                    expect(field.jsonTextTypeFieldName).toBe('text_type');
                });
            });

            describe('richTextAttr', function() {
                it('With allowRichText=true', function() {
                    field.allowRichText = true;

                    expect(field.richTextAttr()).toBe('myFieldRichText');
                });

                it('With allowRichText=false', function() {
                    field.allowRichText = false;

                    expect(field.richTextAttr()).toBe(null);
                });
            });
        });

        describe('Methods', function() {
            describe('render', function() {
                beforeEach(function() {
                    field.$el.addClass('editable');
                    rawTextFields.extra_data = {
                        my_field: '**Hello world**',
                        my_field_text_type: 'markdown',
                    };
                });

                describe('With allowRichText=true', function() {
                    beforeEach(function() {
                        field.allowRichText = true;
                    });

                    it('With richText=true', function() {
                        rawTextFields.extra_data.my_field_text_type =
                            'markdown';

                        field.render();

                        expect(field.inlineEditorView.textEditor.richText)
                            .toBe(true);
                        expect(field.inlineEditorView.options.rawValue)
                            .toBe('**Hello world**');
                    });

                    it('With richText=false', function() {
                        rawTextFields.extra_data.my_field_text_type = 'plain';

                        field.render();

                        expect(field.inlineEditorView.textEditor.richText)
                            .toBe(false);
                        expect(field.inlineEditorView.options.rawValue)
                            .toBe('**Hello world**');
                    });
                });
            });

            describe('_formatField', function() {
                it('With built-in field', function() {
                    field.useExtraData = false;

                    draft.set('myField', 'Hello world');

                    field._formatField();
                    expect(field.$el.text()).toBe('Hello world');
                });

                it('With custom field', function() {
                    editorView.addFieldView(field);

                    extraData.my_field = 'Hello world';

                    field._formatField();
                    expect(field.$el.text()).toBe('Hello world');
                });

                it('With formatValue as function', function() {
                    field.formatValue = function(value) {
                        this.$el.text(`[${value}]`);
                    };

                    extraData.my_field = 'Hello world';

                    field._formatField();
                    expect(field.$el.text()).toBe('[Hello world]');
                });
            });

            describe('_getInlineEditorClass', function() {
                it('With allowRichText=true', function() {
                    field.allowRichText = true;

                    expect(field._getInlineEditorClass())
                        .toBe(RB.RichTextInlineEditorView);
                });

                it('With allowRichText=false', function() {
                    field.allowRichText = false;

                    expect(field._getInlineEditorClass())
                        .toBe(RB.InlineEditorView);
                });
            });

            describe('_loadRichTextValue', function() {
                beforeEach(function() {
                    field.allowRichText = true;
                });

                describe('With built-in field', function() {
                    beforeEach(function() {
                        field.useExtraData = false;
                    });

                    it('With value=undefined', function() {
                        draft.set('myFieldRichText', undefined);
                        expect(field._loadRichTextValue()).toBe(undefined);
                    });

                    it('With value=false', function() {
                        draft.set('myFieldRichText', false);
                        expect(field._loadRichTextValue()).toBe(false);
                    });

                    it('With value=true', function() {
                        draft.set('myFieldRichText', true);
                        expect(field._loadRichTextValue()).toBe(true);
                    });
                });

                describe('With custom field', function() {
                    it('With textType=undefined', function() {
                        expect(field._loadRichTextValue()).toBe(undefined);
                    });

                    it('With textType=plain', function() {
                        rawTextFields.extra_data.my_field_text_type = 'plain';
                        expect(field._loadRichTextValue()).toBe(false);
                    });

                    it('With textType=markdown', function() {
                        rawTextFields.extra_data.my_field_text_type =
                            'markdown';
                        expect(field._loadRichTextValue()).toBe(true);
                    });

                    it('With textType=invalid value', function() {
                        rawTextFields.extra_data.my_field_text_type = 'html';

                        try {
                            field._loadRichTextValue();
                        } catch (e) {
                            // Do nothing.
                        }

                        expect(console.assert).toHaveBeenCalledWith(
                            false,
                            'Text type "html" in field "my_field_text_type" ' +
                            'not supported.');
                    });
                });
            });
        });
    });

    describe('MultilineTextFieldView', function() {
        describe('Initialization from DOM', function() {
            let $el;

            beforeEach(function() {
                $el = $('<span data-allow-markdown="true"/>')
                    .text('DOM text value');
            });

            describe('allowRichText', function() {
                it('allow-markdown=true', function() {
                    field = new MultilineTextFieldView({
                        el: $el,
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(field.allowRichText).toBe(true);
                });

                it('allow-markdown=false', function() {

                    field = new MultilineTextFieldView({
                        el: $el.attr('data-allow-markdown', 'false'),
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(field.allowRichText).toBe(false);
                });

                it('allow-markdown unset', function() {
                    field = new MultilineTextFieldView({
                        el: $el.removeAttr('data-allow-markdown'),
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(field.allowRichText).toBe(undefined);
                });
            });

            describe('Text value', function() {
                it('raw-value set', function() {

                    field = new MultilineTextFieldView({
                        el: $el.attr('data-raw-value', 'attr text value'),
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(extraData.foo).toBe('attr text value');
                    expect($el.attr('data-raw-value')).toBe(undefined);
                });

                it('raw-value unset', function() {
                    field = new MultilineTextFieldView({
                        el: $el,
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(extraData.foo).toBe('DOM text value');
                });
            });

            describe('Text type value', function() {
                it('rich-text class present', function() {
                    field = new MultilineTextFieldView({
                        el: $el.addClass('rich-text'),
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(extraData.foo_text_type).toBe('markdown');
                });

                it('rich-text class not present', function() {
                    field = new MultilineTextFieldView({
                        el: $el,
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(extraData.foo_text_type).toBe('plain');
                });
            });
        });
    });
});
