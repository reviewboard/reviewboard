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

        this.options = _.defaults(options || {}, this.defaultOptions);
    },

    /*
     * Renders the view.
     *
     * This will create a CodeMirror editor internally, and will set any
     * appropriate options on it, based on what was provided to
     * MarkdownEditorView.
     */
    render: function() {
        var codeMirrorOptions = {
            mode: 'gfm',
            lineWrapping: true,
            extraKeys: {
                'Tab': false
            }
        };

        if (this.options.autoSize) {
            codeMirrorOptions.viewportMargin = Infinity;
        }

        this._codeMirror = CodeMirror(this.el, codeMirrorOptions);

        if (this.options.minHeight) {
            $(this._codeMirror.getWrapperElement())
                .css('min-height', this.options.minHeight);
        }

        return this;
    },

    /*
     * Sets the text in the editor.
     */
    setText: function(text) {
        if (text !== this._codeMirror.getValue()) {
            this._codeMirror.setValue(text);
        }
    },

    /*
     * Returns the text in the editor.
     */
    getText: function() {
        return this._codeMirror.getValue();
    },

    /*
     * Sets the size of the editor.
     */
    setSize: function(width, height) {
        this._codeMirror.setSize(width, height);
    },

    /*
     * Shows the editor.
     */
    show: function() {
        this.$el.show();
        this._codeMirror.refresh();
    },

    /*
     * Hides the editor.
     */
    hide: function() {
        this.$el.hide();
    },

    /*
     * Focuses the editor.
     */
    focus: function() {
        this._codeMirror.focus();
    },

    /*
     * Blurs the editor.
     */
    blur: function() {
        this.element.blur();
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
                    markdownEditor._codeMirror.refresh();
                });

                markdownEditor.$el.data('markdown-editor', markdownEditor);

                return markdownEditor.$el;
            },

            setFieldValue: function(editor, value) {
                markdownEditor.setText(value);
            },

            getFieldValue: function(editor) {
                return markdownEditor.getText();
            }
        };
    }
});
