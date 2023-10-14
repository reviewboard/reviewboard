import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import { UserSession } from 'reviewboard/common';
import {
    DnDUploader,
    TextEditorView,
} from 'reviewboard/ui';


suite('rb/ui/views/TextEditorView', function() {
    let view;

    beforeEach(function() {
        DnDUploader.create();
    });

    afterEach(function() {
        DnDUploader.instance = null;
    });

    describe('Construction', function() {
        it('Initial text', function() {
            view = new TextEditorView({
                text: 'Test',
            });
            view.render();

            expect(view.getText()).toBe('Test');
        });

        describe('Text field wrapper', function() {
            it('If plain text', function() {
                view = new TextEditorView({
                    richText: false,
                });
                view.render();
                view.show();

                expect(view.richText).toBe(false);
                expect(view.$el.children('textarea').length).toBe(1);
                expect(view.$el.children('.CodeMirror').length).toBe(0);
            });

            it('If Markdown', function() {
                view = new TextEditorView({
                    richText: true,
                });
                view.render();
                view.show();

                expect(view.richText).toBe(true);
                expect(view.$el.children('textarea').length).toBe(0);
                expect(view.$el.children('.CodeMirror').length).toBe(1);
            });
        });

        describe('Default richText', function() {
            describe('If user default is true', function() {
                beforeEach(function() {
                    UserSession.instance.set('defaultUseRichText', true);
                });

                it('And richText unset', function() {
                    view = new TextEditorView();
                    view.render();
                    view.show();

                    expect(view.richText).toBe(true);
                    expect(view.$el.children('textarea').length).toBe(0);
                    expect(view.$el.children('.CodeMirror').length).toBe(1);
                });

                it('And richText=true', function() {
                    view = new TextEditorView({
                        richText: true,
                    });
                    view.render();
                    view.show();

                    expect(view.richText).toBe(true);
                    expect(view.$el.children('textarea').length).toBe(0);
                    expect(view.$el.children('.CodeMirror').length).toBe(1);
                });

                it('And richText=false', function() {
                    view = new TextEditorView({
                        richText: false,
                    });
                    view.render();
                    view.show();

                    expect(view.richText).toBe(true);
                    expect(view.$el.children('textarea').length).toBe(0);
                    expect(view.$el.children('.CodeMirror').length).toBe(1);
                });
            });

            describe('If user default is false', function() {
                beforeEach(function() {
                    UserSession.instance.set('defaultUseRichText', false);
                });

                it('And richText unset', function() {
                    view = new TextEditorView();
                    view.render();
                    view.show();

                    expect(view.richText).toBe(false);
                    expect(view.$el.children('textarea').length).toBe(1);
                    expect(view.$el.children('.CodeMirror').length).toBe(0);
                });

                it('And richText=true', function() {
                    view = new TextEditorView({
                        richText: true,
                    });
                    view.render();
                    view.show();

                    expect(view.richText).toBe(true);
                    expect(view.$el.children('textarea').length).toBe(0);
                    expect(view.$el.children('.CodeMirror').length).toBe(1);
                });

                it('And richText=false', function() {
                    view = new TextEditorView({
                        richText: false,
                    });
                    view.render();
                    view.show();

                    expect(view.richText).toBe(false);
                    expect(view.$el.children('textarea').length).toBe(1);
                    expect(view.$el.children('.CodeMirror').length).toBe(0);
                });
            });
        });
    });

    describe('Operations', function() {
        describe('bindRichTextAttr', function() {
            let myModel;

            beforeEach(function() {
                myModel = new Backbone.Model({
                    richText: false,
                });

                view = new TextEditorView();
            });

            it('Updates on change', function() {
                view.bindRichTextAttr(myModel, 'richText');
                expect(view.richText).toBe(false);

                myModel.set('richText', true);
                expect(view.richText).toBe(true);
            });

            describe('Initial richText value', function() {
                it('true', function() {
                    myModel.set('richText', true);
                    view.bindRichTextAttr(myModel, 'richText');

                    expect(view.richText).toBe(true);
                });

                it('false', function() {
                    myModel.set('richText', false);
                    view.bindRichTextAttr(myModel, 'richText');

                    expect(view.richText).toBe(false);
                });
            });
        });

        describe('bindRichTextCheckbox', function() {
            let $checkbox;

            beforeEach(function() {
                $checkbox = $('<input type="checkbox">');

                view = new TextEditorView();
                view.setRichText(false);
            });

            it('Checkbox reflects richText', function() {
                view.bindRichTextCheckbox($checkbox);
                expect($checkbox.prop('checked')).toBe(false);

                view.setRichText(true);
                expect($checkbox.prop('checked')).toBe(true);
            });

            describe('richText reflects checkbox', function() {
                it('Checked', function() {
                    view.setRichText(false);
                    view.bindRichTextCheckbox($checkbox);

                    $checkbox
                        .prop('checked', true)
                        .triggerHandler('change');

                    expect(view.richText).toBe(true);
                });

                it('Unchecked', function() {
                    view.setRichText(true);
                    view.bindRichTextCheckbox($checkbox);

                    $checkbox
                        .prop('checked', false)
                        .triggerHandler('change');

                    expect(view.richText).toBe(false);
                });
            });

            describe('Initial checked state', function() {
                it('richText=true', function() {
                    view.setRichText(true);
                    view.bindRichTextCheckbox($checkbox);

                    expect($checkbox.prop('checked')).toBe(true);
                });

                it('richText=false', function() {
                    view.setRichText(false);
                    view.bindRichTextCheckbox($checkbox);

                    expect($checkbox.prop('checked')).toBe(false);
                });
            });
        });

        describe('bindRichTextVisibility', function() {
            let $el;

            beforeEach(function() {
                $el = $('<div>');

                view = new TextEditorView();
                view.setRichText(false);
            });

            describe('Initial visibility', function() {
                it('richText=true', function() {
                    $el.hide();

                    view.setRichText(true);
                    view.bindRichTextVisibility($el);

                    /*
                     * Chrome returns an empty string, while Firefox returns
                     * "block".
                     */
                    const display = $el.css('display');
                    expect(display === 'block' || display === '').toBe(true);
                });

                it('richText=false', function() {
                    view.bindRichTextVisibility($el);

                    expect($el.css('display')).toBe('none');
                });
            });

            describe('Toggles visibility on change', function() {
                it('richText=true', function() {
                    $el.hide();

                    view.bindRichTextVisibility($el);
                    expect($el.css('display')).toBe('none');

                    view.setRichText(true);
                    /*
                     * Chrome returns an empty string, while Firefox returns
                     * "block".
                     */
                    const display = $el.css('display');
                    expect(display === 'block' || display === '').toBe(true);
                });

                it('richText=false', function() {
                    view.setRichText(true);
                    view.bindRichTextVisibility($el);

                    /*
                     * Chrome returns an empty string, while Firefox returns
                     * "block".
                     */
                    const display = $el.css('display');
                    expect(display === 'block' || display === '').toBe(true);

                    view.setRichText(false);
                    expect($el.css('display')).toBe('none');
                });
            });
        });

        describe('setRichText', function() {
            it('Emits change:richText', function() {
                let emitted = false;

                view.on('change:richText', function() {
                    emitted = true;
                });

                view.show();
                view.richText = false;
                view.setRichText(true);

                expect(emitted).toBe(true);
            });

            it('Emits change', function() {
                let emitted = false;

                view.on('change', function() {
                    emitted = true;
                });

                view.show();
                view.richText = false;
                view.setRichText(true);

                expect(emitted).toBe(true);
            });

            it('Marks dirty', function() {
                view.show();
                view.richText = false;
                expect(view.isDirty()).toBe(false);

                view.setRichText(true);
                expect(view.isDirty()).toBe(true);
            });

            describe('Markdown to Text', function() {
                beforeEach(function() {
                    view = new TextEditorView({
                        richText: true,
                    });
                    view.render();
                });

                it('If shown', function() {
                    view.show();
                    view.setRichText(false);

                    expect(view.richText).toBe(false);
                    expect(view.$el.children('textarea').length).toBe(1);
                    expect(view.$el.children('.CodeMirror').length).toBe(0);
                });

                it('If hidden', function() {
                    view.setRichText(false);

                    expect(view.richText).toBe(false);
                    expect(view.$el.children('textarea').length).toBe(0);
                    expect(view.$el.children('.CodeMirror').length).toBe(0);
                });
            });

            describe('Text to Markdown', function() {
                beforeEach(function() {
                    view = new TextEditorView({
                        richText: false,
                    });
                    view.render();
                });

                it('If shown', function() {
                    view.show();
                    view.setRichText(true);

                    expect(view.richText).toBe(true);
                    expect(view.$el.children('textarea').length).toBe(0);
                    expect(view.$el.children('.CodeMirror').length).toBe(1);
                });

                it('If hidden', function() {
                    view.setRichText(true);

                    expect(view.richText).toBe(true);
                    expect(view.$el.children('textarea').length).toBe(0);
                    expect(view.$el.children('.CodeMirror').length).toBe(0);
                });
            });
        });

        describe('setText', function() {
            describe('If shown', function() {
                it('If plain text', function() {
                    view = new TextEditorView({
                        richText: false,
                    });
                    view.show();
                    view.setText('Test');

                    expect(view.$('textarea').val()).toBe('Test');
                });

                it('If Markdown', function() {
                    view = new TextEditorView({
                        richText: true,
                    });
                    view.show();
                    view.setText('Test');

                    expect(view._editor._codeMirror.getValue()).toBe('Test');
                });
            });

            it('If hidden', function() {
                view = new TextEditorView();
                view.setText('Test');

                expect(view.getText()).toBe('Test');
            });
        });

        describe('getText', function() {
            it('If plain text', function() {
                view = new TextEditorView({
                    richText: false,
                });
                view.show();
                view.setText('Test');

                expect(view.getText()).toBe('Test');
            });

            it('If Markdown', function() {
                view = new TextEditorView({
                    richText: true,
                });
                view.show();
                view.setText('Test');

                expect(view.getText()).toBe('Test');
            });
        });

        describe('insertLine', function() {
            it('If plain text', function() {
                view = new TextEditorView({
                    richText: false,
                });
                view.show();
                view.setText('Test');
                view.insertLine('Test');

                expect(view.getText()).toBe('Test\nTest');
            });

            it('If Markdown', function() {
                view = new TextEditorView({
                    richText:true,
                });
                view.show();
                view.setText('Test');
                view.insertLine('Test');

                expect(view.getText()).toBe('Test\nTest');
            });
        });

        describe('show', function() {
            it('registers drop target if rich text', function() {
                spyOn(DnDUploader.instance, 'registerDropTarget');

                view = new TextEditorView({
                    richText: true,
                });
                view.show();

                expect(DnDUploader.instance.registerDropTarget)
                    .toHaveBeenCalled();
            });

            it('does not register drop target if plain text', function() {
                spyOn(DnDUploader.instance, 'registerDropTarget');

                view = new TextEditorView({
                    richText: false,
                });
                view.show();

                expect(DnDUploader.instance.registerDropTarget)
                    .not.toHaveBeenCalled();
            });
        });

        describe('hide', function() {
            it('disables drop target', function() {
                spyOn(DnDUploader.instance, 'unregisterDropTarget');

                view = new TextEditorView({
                    richText: true,
                });
                view.show();
                view.hide();

                expect(DnDUploader.instance.unregisterDropTarget)
                    .toHaveBeenCalled();
            });
        });
    });

    describe('Drag and Drop', function() {
        beforeEach(function() {
            view = new TextEditorView({
                richText: true,
            });
        });

        describe('_isImage', function() {
            it('correctly checks mimetype', function() {
                const file = {
                    name: 'testimage.jpg',
                    type: 'image/jpeg',
                };

                expect(view._isImage(file)).toBe(true);
            });

            it('checks filename extension', function() {
                const file = {
                    name: 'testimage.jpg',
                };

                expect(view._isImage(file)).toBe(true);
            });

            it('returns false when given invalid type', function() {
                const file = {
                    name: 'testimage.jps',
                    type: 'application/json',
                };

                expect(view._isImage(file)).toBe(false);
            });
        });
    });

    describe('Markdown formatting toolbar', () => {
        describe('Rich text', () => {
            it('Enabled', () => {
                view = new TextEditorView({
                    richText: true,
                });
                view.show();

                expect(view.$('.rb-c-formatting-toolbar').length)
                    .toBe(1);
            });

            it('Disabled', () => {
                view = new TextEditorView({
                    richText: false,
                });
                view.show();

                expect(view.$('.rb-c-formatting-toolbar').length)
                    .toBe(0);
            });
        });

        describe('Buttons', () => {
            let codeMirror;

            beforeEach(() => {
                view = new TextEditorView({
                    richText: true,
                });
                view.show();

                codeMirror = view._editor._codeMirror;
            });

            describe('Bold', () => {
                it('Empty selection with no text toggles syntax', () => {
                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-bold').click();

                    expect(view.getText()).toBe('****');
                    expect(codeMirror.getCursor().ch).toBe(2);

                    view.$('.rb-c-formatting-toolbar__btn-bold').click();

                    expect(view.getText()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(0);
                });

                it('Empty selection with cursor in unformatted text inserts syntax around text', () => {
                    view.setText('Test');

                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-bold').click();

                    expect(view.getText()).toBe('**Test**');
                    expect(codeMirror.getCursor().ch).toBe(6);
                });

                it('Empty selection with cursor in formatted text removes syntax around text', () => {
                    view.setText('**Test**');
                    codeMirror.setSelection({ch: 2, line: 0},
                                            {ch: 6, line: 0});

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-bold').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Unformatted text selection inserts syntax around text', () => {
                    view.setText('Test');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-bold').click();

                    expect(view.getText()).toBe('**Test**');
                    expect(codeMirror.getCursor().ch).toBe(8);
                })

                it('Formatted text selection with only text removes syntax', () => {
                    view.setText('**Test**');
                    codeMirror.setSelection({ch: 2, line: 0},
                                            {ch: 6, line: 0});

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-bold').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Formatted text selection including formatting removes syntax', () => {
                    view.setText('**Test**');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('**Test**');

                    view.$('.rb-c-formatting-toolbar__btn-bold').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });
            });

            describe('Italic', () => {
                it('Empty selection with no text toggles syntax', () => {
                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-italic').click();

                    expect(view.getText()).toBe('__');
                    expect(codeMirror.getCursor().ch).toBe(1);

                    view.$('.rb-c-formatting-toolbar__btn-italic').click();

                    expect(view.getText()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(0);
                });

                it('Empty selection with cursor in unformatted text inserts syntax around text', () => {
                    view.setText('Test');

                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-italic').click();

                    expect(view.getText()).toBe('_Test_');
                    expect(codeMirror.getCursor().ch).toBe(5);
                });

                it('Empty selection with cursor in formatted text removes syntax around text', () => {
                    view.setText('_Test_');
                    codeMirror.setSelection({ch: 1, line: 0},
                                            {ch: 5, line: 0});

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-italic').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Unformatted text selection inserts syntax around text', () => {
                    view.setText('Test');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-italic').click();

                    expect(view.getText()).toBe('_Test_');
                    expect(codeMirror.getCursor().ch).toBe(6);
                })

                it('Formatted text selection with only text removes syntax', () => {
                    view.setText('_Test_');
                    codeMirror.setSelection({ch: 1, line: 0},
                                            {ch: 5, line: 0});

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-italic').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Formatted text selection including formatting removes syntax', () => {
                    view.setText('_Test_');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('_Test_');

                    view.$('.rb-c-formatting-toolbar__btn-italic').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });
            });

            describe('Strikethrough', () => {
                it('Empty selection with no text toggles syntax', () => {
                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-strikethrough').click();

                    expect(view.getText()).toBe('~~~~');
                    expect(codeMirror.getCursor().ch).toBe(2);

                    view.$('.rb-c-formatting-toolbar__btn-strikethrough').click();

                    expect(view.getText()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(0);
                });

                it('Empty selection with cursor in unformatted text inserts syntax around text', () => {
                    view.setText('Test');

                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-strikethrough').click();

                    expect(view.getText()).toBe('~~Test~~');
                    expect(codeMirror.getCursor().ch).toBe(6);
                });

                it('Empty selection with cursor in formatted text removes syntax around text', () => {
                    view.setText('~~Test~~');
                    codeMirror.setSelection({ch: 2, line: 0},
                                            {ch: 6, line: 0});

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-strikethrough').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Unformatted text selection inserts syntax around text', () => {
                    view.setText('Test');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-strikethrough').click();

                    expect(view.getText()).toBe('~~Test~~');
                    expect(codeMirror.getCursor().ch).toBe(8);
                })

                it('Formatted text selection with only text removes syntax', () => {
                    view.setText('~~Test~~');
                    codeMirror.setSelection({ch: 2, line: 0},
                                            {ch: 6, line: 0});

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-strikethrough').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Formatted text selection including formatting removes syntax', () => {
                    view.setText('~~Test~~');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('~~Test~~');

                    view.$('.rb-c-formatting-toolbar__btn-strikethrough').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });
            });

            describe('Code', () => {
                it('Empty selection with no text toggles syntax', () => {
                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-code').click();

                    expect(view.getText()).toBe('``');
                    expect(codeMirror.getCursor().ch).toBe(1);

                    view.$('.rb-c-formatting-toolbar__btn-code').click();

                    expect(view.getText()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(0);
                });

                it('Empty selection with cursor in unformatted text inserts syntax around text', () => {
                    view.setText('Test');

                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-code').click();

                    expect(view.getText()).toBe('`Test`');
                    expect(codeMirror.getCursor().ch).toBe(5);
                });

                it('Empty selection with cursor in formatted text removes syntax around text', () => {
                    view.setText('`Test`');
                    codeMirror.setSelection({ch: 1, line: 0},
                                            {ch: 5, line: 0});

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-code').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Unformatted text selection inserts syntax around text', () => {
                    view.setText('Test');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-code').click();

                    expect(view.getText()).toBe('`Test`');
                    expect(codeMirror.getCursor().ch).toBe(6);
                })

                it('Formatted text selection with only text removes syntax', () => {
                    view.setText('`Test`');
                    codeMirror.setSelection({ch: 1, line: 0},
                                            {ch: 5, line: 0});

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-code').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Formatted text selection including formatting removes syntax', () => {
                    view.setText('`Test`');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('`Test`');

                    view.$('.rb-c-formatting-toolbar__btn-code').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });
            });

            describe('Unordered list', () => {
                it('Empty selection with no text toggles syntax', () => {
                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-list-ul').click();

                    expect(view.getText()).toBe('- ');
                    expect(codeMirror.getCursor().ch).toBe(2);

                    view.$('.rb-c-formatting-toolbar__btn-list-ul').click();

                    expect(view.getText()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(0);
                });

                it('Empty selection with cursor in text toggles syntax', () => {
                    view.setText('Test');
                    codeMirror.setCursor({ch: 2, line: 0});

                    view.$('.rb-c-formatting-toolbar__btn-list-ul').click();

                    expect(view.getText()).toBe('- Test');
                    expect(codeMirror.getCursor().ch).toBe(4);

                    view.$('.rb-c-formatting-toolbar__btn-list-ul').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(2);
                });

                it('Unformatted text selection toggles syntax', () => {
                    view.setText('Test');
                    codeMirror.execCommand('selectAll');

                    view.$('.rb-c-formatting-toolbar__btn-list-ul').click();

                    expect(view.getText()).toBe('- Test');
                    expect(codeMirror.getCursor().ch).toBe(6);

                    codeMirror.execCommand('selectAll');

                    view.$('.rb-c-formatting-toolbar__btn-list-ul').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Formatted text selection with only text removes syntax', () => {
                    view.setText('- Test');
                    codeMirror.setSelection({ch: 2, line: 0},
                                            {ch: 6, line: 0});

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-list-ul').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Formatted text selection including formatting removes syntax', () => {
                    view.setText('- Test');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('- Test');

                    view.$('.rb-c-formatting-toolbar__btn-list-ul').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getSelection()).toBe('Test');
                });

                it('Lines with multiple text groups get syntax added to beginning of the line', () => {
                    view.setText('Test more text');
                    codeMirror.setCursor({ch: 6, line: 0});

                    view.$('.rb-c-formatting-toolbar__btn-list-ul').click();

                    expect(view.getText()).toBe('- Test more text');
                    expect(codeMirror.getCursor().ch).toBe(8);
                });
            });

            describe('Ordered list', () => {
                it('Empty selection with no text toggles syntax', () => {
                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-list-ol').click();

                    expect(view.getText()).toBe('1. ');
                    expect(codeMirror.getCursor().ch).toBe(3);

                    view.$('.rb-c-formatting-toolbar__btn-list-ol').click();

                    expect(view.getText()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(0);
                });

                it('Empty selection with cursor in text toggles syntax', () => {
                    view.setText('Test');
                    codeMirror.setCursor({ch: 2, line: 0});

                    view.$('.rb-c-formatting-toolbar__btn-list-ol').click();

                    expect(view.getText()).toBe('1. Test');
                    expect(codeMirror.getCursor().ch).toBe(5);

                    view.$('.rb-c-formatting-toolbar__btn-list-ol').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(2);
                });

                it('Unformatted text selection toggles syntax', () => {
                    view.setText('Test');
                    codeMirror.execCommand('selectAll');

                    view.$('.rb-c-formatting-toolbar__btn-list-ol').click();

                    expect(view.getText()).toBe('1. Test');
                    expect(codeMirror.getCursor().ch).toBe(7);

                    codeMirror.execCommand('selectAll');

                    view.$('.rb-c-formatting-toolbar__btn-list-ol').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Formatted text selection with only text removes syntax', () => {
                    view.setText('1. Test');
                    codeMirror.setSelection({ch: 3, line: 0},
                                            {ch: 7, line: 0});

                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-list-ol').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Formatted text selection including formatting removes syntax', () => {
                    view.setText('1. Test');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('1. Test');

                    view.$('.rb-c-formatting-toolbar__btn-list-ol').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getSelection()).toBe('Test');
                });

                it('Lines with multiple text groups get syntax added to beginning of the line', () => {
                    view.setText('Test more text');
                    codeMirror.setCursor({ch: 6, line: 0});

                    view.$('.rb-c-formatting-toolbar__btn-list-ol').click();

                    expect(view.getText()).toBe('1. Test more text');
                    expect(codeMirror.getCursor().ch).toBe(9);
                });
            });

            describe('Link', () => {
                it('Empty selection with no text toggles syntax', () => {
                    expect(codeMirror.getSelection()).toBe('');

                    view.$('.rb-c-formatting-toolbar__btn-link').click();

                    expect(view.getText()).toBe('[](url)');
                    expect(codeMirror.getCursor().ch).toBe(1);

                    view.$('.rb-c-formatting-toolbar__btn-link').click();

                    expect(view.getText()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(0);
                });

                it('Empty selection with cursor in text toggles syntax', () => {
                    view.setText('Test');
                    codeMirror.setCursor({ch: 2, line: 0});

                    view.$('.rb-c-formatting-toolbar__btn-link').click();

                    expect(view.getText()).toBe('[Test](url)');
                    expect(codeMirror.getSelection()).toBe('url');
                    expect(codeMirror.getCursor().ch).toBe(10);

                    view.$('.rb-c-formatting-toolbar__btn-link').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getSelection()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Unformatted text selection toggles syntax', () => {
                    view.setText('Test');
                    codeMirror.execCommand('selectAll');

                    view.$('.rb-c-formatting-toolbar__btn-link').click();

                    expect(view.getText()).toBe('[Test](url)');
                    expect(codeMirror.getSelection()).toBe('url');
                    expect(codeMirror.getCursor().ch).toBe(10);

                    view.$('.rb-c-formatting-toolbar__btn-link').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getSelection()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Formatted text selection with only text removes syntax', () => {
                    view.setText('[Test](example.com)');
                    codeMirror.setSelection({ch: 1, line: 0},
                                            {ch: 5, line: 0});
                    expect(codeMirror.getSelection()).toBe('Test');

                    view.$('.rb-c-formatting-toolbar__btn-link').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getSelection()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });

                it('Formatted text selection including formatting removes syntax', () => {
                    view.setText('[Test](example.com)');
                    codeMirror.execCommand('selectAll');

                    expect(codeMirror.getSelection()).toBe('[Test](example.com)');

                    view.$('.rb-c-formatting-toolbar__btn-link').click();

                    expect(view.getText()).toBe('Test');
                    expect(codeMirror.getSelection()).toBe('');
                    expect(codeMirror.getCursor().ch).toBe(4);
                });
            });
        });
    });
});
