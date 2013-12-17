/*
 * Provides an editor for editing Markdown text.
 *
 * This makes use of CodeMirror internally to do the editing. All Markdown
 * content will be formatted as the user types, making it easier to notice
 * when a stray _ or ` will cause Markdown-specific behavior.
 */
RB.MarkdownEditorView = Backbone.View.extend({
    className: 'markdown-editor',

    defaultOptions: {
        autoSize: true,
        minHeight: 70
    },

    events: {
        'focus': 'focus'
    },

    /*
     * Initializes the view with any provided options.
     */
    initialize: function(options) {
        this._codeMirror = null;
        this._value = '';

        this.options = _.defaults(options || {}, this.defaultOptions);
    },

    /*
     * Returns whether or not the editor's contents have changed.
     */
    isDirty: function() {
        return this._codeMirror ? !this._codeMirror.isClean() : false;
    },

    /*
     * Sets the text in the editor.
     */
    setText: function(text) {
        if (text !== this.getText()) {
            if (this._codeMirror) {
                this._codeMirror.setValue(text);
            } else {
                this._value = text;
            }
        }
    },

    /*
     * Returns the text in the editor.
     */
    getText: function() {
        return this._codeMirror ? this._codeMirror.getValue() : this._value;
    },

    /*
     * Sets the size of the editor.
     */
    setSize: function(width, height) {
        if (this._codeMirror) {
            this._codeMirror.setSize(width, height);
        }
    },

    /*
     * Shows the editor.
     */
    show: function() {
        this.$el.show();
        this._showEditor();
    },

    /*
     * Hides the editor.
     */
    hide: function() {
        this._hideEditor();
        this.$el.hide();
    },

    /*
     * Focuses the editor.
     */
    focus: function() {
        if (this._codeMirror) {
            this._codeMirror.focus();
        }
    },

    /*
     * Blurs the editor.
     */
    blur: function() {
        this.element.blur();
    },

    /*
     * Shows the actual CodeMirror editor.
     *
     * Any stored text will be transferred to the editor, and the editor
     * will take control over all operations.
     */
    _showEditor: function() {
        var codeMirrorOptions = {
            mode: 'gfm',
            lineWrapping: true,
            extraKeys: {
                'Enter': 'newlineAndIndentContinueMarkdownList',
                'Shift-Tab': false,
                'Tab': false
            }
        };

        if (this.options.autoSize) {
            codeMirrorOptions.viewportMargin = Infinity;
        }

        this._codeMirror = CodeMirror(this.el, codeMirrorOptions);
        this._codeMirror.setValue(this._value);
        this._value = '';

        if (this.options.minHeight) {
            $(this._codeMirror.getWrapperElement())
                .css('min-height', this.options.minHeight);
        }

        this.focus();
    },

    /*
     * Hides the actual CodeMirror editor.
     *
     * The last value from the editor will be stored for later retrieval.
     */
    _hideEditor: function() {
        if (this._codeMirror) {
            this._value = this._codeMirror.getValue();
            this.$el.empty();
            this._codeMirror = null;
        }
    }
}, {
    /*
     * Returns options used to display a MarkdownEditorView in an inlineEditor.
     *
     * This will return an options dictionary that can be used with an
     * inlineEditor. The inlineEditor will make use of the MarkdownEditorView
     * instead of a textarea.
     *
     * This can take options for the MarkdownEditorView to change the default
     * behavior.
     */
    getInlineEditorOptions: function(options) {
        var markdownEditor;

        return {
            matchHeight: false,

            createMultilineField: function(editor) {
                markdownEditor = new RB.MarkdownEditorView(options);
                markdownEditor.render();

                editor.element.on('beginEdit', function() {
                    markdownEditor._showEditor();
                });

                editor.element.on('cancel complete', function() {
                    markdownEditor._hideEditor();
                });

                markdownEditor.$el.data('markdown-editor', markdownEditor);

                return markdownEditor.$el;
            },

            setFieldValue: function(editor, value) {
                markdownEditor.setText(value);
            },

            getFieldValue: function(editor) {
                return markdownEditor.getText();
            },

            isFieldDirty: function(editor) {
                return markdownEditor.isDirty();
            }
        };
    }
});
