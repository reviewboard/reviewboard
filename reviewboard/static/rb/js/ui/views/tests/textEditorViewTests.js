suite('rb/ui/views/TextEditorView', function() {
    var view;

    describe('Construction', function() {
        it('Defaults', function() {
            view = new RB.TextEditorView();
            view.render();
            view.show();

            expect(view.richText).toBe(false);
            expect(view.$el.children('textarea').length).toBe(1);
            expect(view.$el.children('.CodeMirror').length).toBe(0);
        });

        it('Initial text', function() {
            view = new RB.TextEditorView({
                text: 'Test'
            });
            view.render();

            expect(view.getText()).toBe('Test');
        });

        it('If plain text', function() {
            view = new RB.TextEditorView({
                richText: false
            });
            view.render();
            view.show();

            expect(view.richText).toBe(false);
            expect(view.$el.children('textarea').length).toBe(1);
            expect(view.$el.children('.CodeMirror').length).toBe(0);
        });

        it('If Markdown', function() {
            view = new RB.TextEditorView({
                richText: true
            });
            view.render();
            view.show();

            expect(view.richText).toBe(true);
            expect(view.$el.children('textarea').length).toBe(0);
            expect(view.$el.children('.CodeMirror').length).toBe(1);
        });
    });

    describe('Operations', function() {
        describe('setRichText', function() {
            describe('Markdown to Text', function() {
                beforeEach(function() {
                    view = new RB.TextEditorView({
                        richText: true
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
                        richText: false
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
                        richText: false
                    });
                    view.show();
                    view.setText('Test');

                    expect(view.$('textarea').val()).toBe('Test');
                });

                it('If Markdown', function() {
                    view = new RB.TextEditorView({
                        richText: true
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
                    richText: false
                });
                view.show();
                view.setText('Test');

                expect(view.getText()).toBe('Test');
            });

            it('If Markdown', function() {
                view = new RB.TextEditorView({
                    richText: true
                });
                view.show();
                view.setText('Test');

                expect(view.getText()).toBe('Test');
            });
        });
    });

    describe('Events', function() {
    });

    describe('inlineEditor options', function() {
        var $el,
            $buttons,
            $markdownCheckbox;

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
            it('Checking', function() {
                setupEditor({
                    richText: false
                });

                $markdownCheckbox
                    .click()
                    .trigger('change');

                expect(view.richText).toBe(true);
            });

            it('Unchecking', function() {
                setupEditor({
                    richText: true
                });

                $markdownCheckbox
                    .click()
                    .trigger('change');

                expect(view.richText).toBe(false);
            });

            describe('Initial state', function() {
                it('If plain text', function() {
                    setupEditor({
                        richText: false
                    });

                    expect($markdownCheckbox.prop('checked')).toBe(false);
                });

                it('If Markdown', function() {
                    setupEditor({
                        richText: true
                    });

                    expect($markdownCheckbox.prop('checked')).toBe(true);
                });
            });
        });
    });
});
