suite('rb/ui/views/TextEditorView', function() {
    let view;

    beforeEach(function() {
        RB.DnDUploader.create();
    });

    afterEach(function() {
        RB.DnDUploader.instance = null;
    });

    describe('Construction', function() {
        it('Initial text', function() {
            view = new RB.TextEditorView({
                text: 'Test',
            });
            view.render();

            expect(view.getText()).toBe('Test');
        });

        describe('Text field wrapper', function() {
            it('If plain text', function() {
                view = new RB.TextEditorView({
                    richText: false,
                });
                view.render();
                view.show();

                expect(view.richText).toBe(false);
                expect(view.$el.children('textarea').length).toBe(1);
                expect(view.$el.children('.CodeMirror').length).toBe(0);
            });

            it('If Markdown', function() {
                view = new RB.TextEditorView({
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
                    RB.UserSession.instance.set('defaultUseRichText', true);
                });

                it('And richText unset', function() {
                    view = new RB.TextEditorView();
                    view.render();
                    view.show();

                    expect(view.richText).toBe(true);
                    expect(view.$el.children('textarea').length).toBe(0);
                    expect(view.$el.children('.CodeMirror').length).toBe(1);
                });

                it('And richText=true', function() {
                    view = new RB.TextEditorView({
                        richText: true,
                    });
                    view.render();
                    view.show();

                    expect(view.richText).toBe(true);
                    expect(view.$el.children('textarea').length).toBe(0);
                    expect(view.$el.children('.CodeMirror').length).toBe(1);
                });

                it('And richText=false', function() {
                    view = new RB.TextEditorView({
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
                    RB.UserSession.instance.set('defaultUseRichText', false);
                });

                it('And richText unset', function() {
                    view = new RB.TextEditorView();
                    view.render();
                    view.show();

                    expect(view.richText).toBe(false);
                    expect(view.$el.children('textarea').length).toBe(1);
                    expect(view.$el.children('.CodeMirror').length).toBe(0);
                });

                it('And richText=true', function() {
                    view = new RB.TextEditorView({
                        richText: true,
                    });
                    view.render();
                    view.show();

                    expect(view.richText).toBe(true);
                    expect(view.$el.children('textarea').length).toBe(0);
                    expect(view.$el.children('.CodeMirror').length).toBe(1);
                });

                it('And richText=false', function() {
                    view = new RB.TextEditorView({
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

                view = new RB.TextEditorView();
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

                view = new RB.TextEditorView();
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

                view = new RB.TextEditorView();
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
                    view = new RB.TextEditorView({
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
                    view = new RB.TextEditorView({
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
                    view = new RB.TextEditorView({
                        richText: false,
                    });
                    view.show();
                    view.setText('Test');

                    expect(view.$('textarea').val()).toBe('Test');
                });

                it('If Markdown', function() {
                    view = new RB.TextEditorView({
                        richText: true,
                    });
                    view.show();
                    view.setText('Test');

                    expect(view._editor._codeMirror.getValue()).toBe('Test');
                });
            });

            it('If hidden', function() {
                view = new RB.TextEditorView();
                view.setText('Test');

                expect(view.getText()).toBe('Test');
            });
        });

        describe('getText', function() {
            it('If plain text', function() {
                view = new RB.TextEditorView({
                    richText: false,
                });
                view.show();
                view.setText('Test');

                expect(view.getText()).toBe('Test');
            });

            it('If Markdown', function() {
                view = new RB.TextEditorView({
                    richText: true,
                });
                view.show();
                view.setText('Test');

                expect(view.getText()).toBe('Test');
            });
        });

        describe('insertLine', function() {
            it('If plain text', function() {
                view = new RB.TextEditorView({
                    richText: false,
                });
                view.show();
                view.setText('Test');
                view.insertLine('Test');

                expect(view.getText()).toBe('Test\nTest');
            });

            it('If Markdown', function() {
                view = new RB.TextEditorView({
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
                spyOn(RB.DnDUploader.instance, 'registerDropTarget');

                view = new RB.TextEditorView({
                    richText: true,
                });
                view.show();

                expect(RB.DnDUploader.instance.registerDropTarget)
                    .toHaveBeenCalled();
            });

            it('does not register drop target if plain text', function() {
                spyOn(RB.DnDUploader.instance, 'registerDropTarget');

                view = new RB.TextEditorView({
                    richText: false,
                });
                view.show();

                expect(RB.DnDUploader.instance.registerDropTarget)
                    .not.toHaveBeenCalled();
            });
        });

        describe('hide', function() {
            it('disables drop target', function() {
                spyOn(RB.DnDUploader.instance, 'unregisterDropTarget');

                view = new RB.TextEditorView({
                    richText: true,
                });
                view.show();
                view.hide();

                expect(RB.DnDUploader.instance.unregisterDropTarget)
                    .toHaveBeenCalled();
            });
        });
    });

    describe('inlineEditor options', function() {
        let $el;
        let $buttons;
        let $markdownCheckbox;

        function setupEditor(options) {
            $el = $('<textarea>').inlineEditor(
                RB.TextEditorView.getInlineEditorOptions(options));
            view = $el.inlineEditor('field').data('text-editor');

            $el.inlineEditor('startEdit');

            $buttons = $el.inlineEditor('buttons');
            expect($buttons.length).toBe(1);

            $markdownCheckbox = $buttons.find('input[type=checkbox]');
            expect($markdownCheckbox.length).toBe(1);
        }

        describe('Rich text checkbox', function() {
            function setChecked(checked) {
                /*
                 * All this is needed to get Firefox and Chrome to play nice.
                 */
                $markdownCheckbox
                    .click()
                    .prop('checked', checked)
                    .trigger('change');
            }

            it('Checking', function() {
                setupEditor({
                    richText: false,
                });

                expect($markdownCheckbox.prop('checked')).toBe(false);

                setChecked(true);

                expect($markdownCheckbox.prop('checked')).toBe(true);
                expect(view.richText).toBe(true);
            });

            it('Unchecking', function() {
                setupEditor({
                    richText: true,
                });

                expect($markdownCheckbox.prop('checked')).toBe(true);

                setChecked(false);

                expect($markdownCheckbox.prop('checked')).toBe(false);
                expect(view.richText).toBe(false);
            });

            it('Resets after cancel', function() {
                setupEditor({
                    richText: true,
                });

                setChecked(false);

                $el.inlineEditor('cancel');

                expect($markdownCheckbox.prop('checked')).toBe(true);
                expect(view.richText).toBe(true);
                expect(view.isDirty()).toBe(false);
            });

            describe('Initial state', function() {
                it('If plain text', function() {
                    setupEditor({
                        richText: false,
                    });

                    expect($markdownCheckbox.prop('checked')).toBe(false);
                });

                it('If Markdown', function() {
                    setupEditor({
                        richText: true,
                    });

                    expect($markdownCheckbox.prop('checked')).toBe(true);
                });
            });
        });
    });

    describe('Drag and Drop', function() {
        beforeEach(function() {
            view = new RB.TextEditorView({
                richText: true,
            });
        });

        describe('_isImage', function() {
            it('correctly checks mimetype', function() {
                const file = {
                    type: 'image/jpeg',
                    name: 'testimage.jpg',
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
                    type: 'application/json',
                    name: 'testimage.jps',
                };

                expect(view._isImage(file)).toBe(false);
            });
        });
    });
});
