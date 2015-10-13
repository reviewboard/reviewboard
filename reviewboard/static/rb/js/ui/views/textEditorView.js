(function() {


var CodeMirrorWrapper,
    TextAreaWrapper;


/*
 * Wraps CodeMirror, providing a standard interface for TextEditorView's usage.
 */
CodeMirrorWrapper = Backbone.View.extend({
    /*
     * Initializes CodeMirrorWrapper.
     *
     * This will set up CodeMirror based on the objects, add it to the parent,
     * and begin listening to events.
     */
    initialize: function(options) {
        var codeMirrorOptions = {
            mode: {
                name: 'gfm',
                classOverrides: {
                    code: 'rb-markdown-code',
                    list1: 'rb-markdown-list1',
                    list2: 'rb-markdown-list2',
                    list3: 'rb-markdown-list3'
                }
            },
            theme: 'rb default',
            lineWrapping: true,
            electricChars: false,
            extraKeys: {
                'Home': 'goLineLeft',
                'End': 'goLineRight',
                'Enter': 'newlineAndIndentContinueMarkdownList',
                'Shift-Tab': false,
                'Tab': false
            }
        };

        if (options.autoSize) {
            codeMirrorOptions.viewportMargin = Infinity;
        }

        this._codeMirror = new CodeMirror(options.parentEl,
                                          codeMirrorOptions);

        this.setElement(this._codeMirror.getWrapperElement());

        if (this.options.minHeight !== undefined) {
            this.$el.css('min-height', this.options.minHeight);
        }

        this._codeMirror.on('viewportChange', _.bind(function() {
            this.$el.triggerHandler('resize');
        }, this));

        this._codeMirror.on('change', _.bind(function() {
            this.trigger('change');
        }, this));
    },

    /*
     * Returns whether or not the editor's contents have changed.
     */
    isDirty: function(initialValue) {
        /*
         * We cannot trust codeMirror's isClean() method.
         *
         * It is also possible for initialValue to be undefined, so we use an
         * empty string in that case instead.
         */
        return (initialValue || '') !== this.getText();
    },

    /*
     * Sets the text in the editor.
     */
    setText: function(text) {
        this._codeMirror.setValue(text);
    },

    /*
     * Returns the text in the editor.
     */
    getText: function() {
        return this._codeMirror.getValue();
    },

    /*
     * Returns the full client height of the content.
     */
    getClientHeight: function() {
        return this._codeMirror.getScrollInfo().clientHeight;
    },

    /*
     * Sets the size of the editor.
     */
    setSize: function(width, height) {
        this._codeMirror.setSize(width, height);
        this._codeMirror.refresh();
    },

    /*
     * Focuses the editor.
     */
    focus: function() {
        this._codeMirror.focus();
    }
});


/*
 * Wraps <textarea>, providing a standard interface for TextEditorView's usage.
 */
TextAreaWrapper = Backbone.View.extend({
    tagName: 'textarea',

    /*
     * Initializes TextAreaWrapper.
     *
     * This will set up the element based on the provided options, begin
     * listening for events, and add the element to the parent.
     */
    initialize: function(options) {
        this.options = options;

        if (options.autoSize) {
            this.$el.autoSizeTextArea();
        }

        this.$el
            .css('width', '100%')
            .appendTo(options.parentEl)
            .on('change keydown keyup keypress', _.bind(function() {
                this.trigger('change');
            }, this));

        if (options.minHeight !== undefined) {
            if (options.autoSize) {
                this.$el.autoSizeTextArea('setMinHeight',
                                          options.minHeight);
            } else {
                this.$el.css('min-height', this.options.minHeight);
            }
        }
    },

    /*
     * Returns whether or not the editor's contents have changed.
     */
    isDirty: function(initialValue) {
        var value = this.el.value || '';

        return value.length !== initialValue.length ||
               value !== initialValue;
    },

    /*
     * Sets the text in the editor.
     */
    setText: function(text) {
        this.el.value = text;

        if (this.options.autoSize) {
            this.$el.autoSizeTextArea('autoSize');
        }
    },

    /*
     * Returns the text in the editor.
     */
    getText: function() {
        return this.el.value;
    },

    /*
     * Returns the full client height of the content.
     */
    getClientHeight: function() {
        return this.el.clientHeight;
    },

    /*
     * Sets the size of the editor.
     */
    setSize: function(width, height) {
        if (width !== null) {
            this.$el.innerWidth(width);
        }

        if (height !== null) {
            if (height === 'auto' && this.options.autoSize) {
                this.$el.autoSizeTextArea('autoSize', true);
            } else {
                this.$el.innerHeight(height);
            }
        }
    },

    /*
     * Focuses the editor.
     */
    focus: function() {
        this.$el.focus();
    }
});


/*
 * Provides an editor for editing plain or Markdown text.
 *
 * The editor allows for switching between plain or Markdown text on-the-fly.
 *
 * When editing plain text, this uses a standard textarea widget.
 *
 * When editing Markdown, this makes use of CodeMirror. All Markdown content
 * will be formatted as the user types, making it easier to notice when a
 * stray _ or ` will cause Markdown-specific behavior.
 */
RB.TextEditorView = Backbone.View.extend({
    className: 'text-editor',

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
        this._editor = null;
        this._prevClientHeight = null;

        this.options = _.defaults(options || {}, this.defaultOptions);
        this.richText = !!this.options.richText;
        this._value = this.options.text || '';
        this._richTextDirty = false;

        if (this.options.bindRichText) {
            this.bindRichTextAttr(this.options.bindRichText.model,
                                  this.options.bindRichText.attrName);
        }

        /*
         * If the user is defaulting to rich text, we're going to want to
         * show the rich text UI by default, even if any bound rich text
         * flag is set to False.
         *
         * This requires cooperation with the template or API results
         * that end up backing this TextEditor. The expectation is that
         * those will be providing escaped data for any plain text, if
         * the user's set to use rich text by default. If this expectation
         * holds, the user will have a consistent experience for any new
         * text fields.
         */
        if (RB.UserSession.instance.get('defaultUseRichText')) {
            this.setRichText(true);
        }
    },

    /*
     * Renders the text editor.
     *
     * This will set the class name on the element, ensuring we have a
     * standard set of styles, even if this editor is bound to an existing
     * element.
     */
    render: function() {
        this.$el.addClass(this.className);

        return this;
    },

    /*
     * Sets whether or not rich text (Markdown) is to be usd.
     *
     * This can dynamically change the text editor to work in plain text
     * or Markdown.
     */
    setRichText: function(richText) {
        if (richText === this.richText) {
            return;
        }

        if (this._editor) {
            this._hideEditor();
            this.richText = richText;
            this._showEditor();

            this._richTextDirty = true;

            this.$el.triggerHandler('resize');
        } else {
            this.richText = richText;
        }

        this.trigger('change:richText', richText);
        this.trigger('change');
    },

    /*
     * Binds a richText attribute on a model to the mode on this editor.
     *
     * This editor's richText setting will stay in sync with the attribute
     * on the given mode.
     */
    bindRichTextAttr: function(model, attrName) {
        this.setRichText(model.get(attrName));

        this.listenTo(model, 'change:' + attrName, function(model, value) {
            this.setRichText(value);
        });
    },

    /*
     * Binds an Enable Markdown checkbox to this text editor.
     *
     * The checkbox will initially be set to the value of the editor's
     * richText property. Toggling the checkbox will then manipulate that
     * property.
     */
    bindRichTextCheckbox: function($checkbox) {
        $checkbox
            .prop('checked', this.richText)
            .on('change', _.bind(function() {
                this.setRichText($checkbox.prop('checked'));
            }, this));

        this.on('change:richText', function() {
            $checkbox.prop('checked', this.richText);
        }, this);
    },

    /*
     * Binds the visibility of an element to the richText property.
     *
     * If richText ist true, the element will be shown. Otherwise, it
     * will be hidden.
     */
    bindRichTextVisibility: function($el) {
        $el.setVisible(this.richText);

        this.on('change:richText', function() {
            $el.setVisible(this.richText);
        }, this);
    },

    /*
     * Returns whether or not the editor's contents have changed.
     */
    isDirty: function(initialValue) {
        return this._editor !== null &&
               (this._richTextDirty ||
                this._editor.isDirty(initialValue || ''));
    },

    /*
     * Sets the text in the editor.
     */
    setText: function(text) {
        if (text !== this.getText()) {
            if (this._editor) {
                this._editor.setText(text);
            } else {
                this._value = text;
            }
        }
    },

    /*
     * Returns the text in the editor.
     */
    getText: function() {
        return this._editor ? this._editor.getText() : this._value;
    },

    /*
     * Sets the size of the editor.
     */
    setSize: function(width, height) {
        if (this._editor) {
            this._editor.setSize(width, height);
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
        if (this._editor) {
            this._editor.focus();
        }
    },

    /*
     * Shows the actual editor wrapper.
     *
     * Any stored text will be transferred to the editor, and the editor
     * will take control over all operations.
     */
    _showEditor: function() {
        var EditorCls;

        if (this.richText) {
            EditorCls = CodeMirrorWrapper;
        } else {
            EditorCls = TextAreaWrapper;
        }

        this._editor = new EditorCls({
            parentEl: this.el,
            autoSize: this.options.autoSize,
            minHeight: this.options.minHeight
        });

        this._editor.setText(this._value);
        this._value = '';
        this._richTextDirty = false;
        this._prevClientHeight = null;

        this._editor.$el.on('resize', _.throttle(_.bind(function() {
            this.$el.triggerHandler('resize');
        }, this), 250));

        this.listenTo(this._editor, 'change', _.throttle(_.bind(function() {
            var clientHeight;

            /*
             * Make sure that the editor wasn't closed before the throttled
             * handler was reached.
             */
            if (this._editor === null) {
                return;
            }

            clientHeight = this._editor.getClientHeight();

            if (clientHeight !== this._prevClientHeight) {
                this._prevClientHeight = clientHeight;
                this.$el.triggerHandler('resize');
            }

            this.trigger('change');
        }, this), 500));

        this.focus();
    },

    /*
     * Hides the actual editor wrapper.
     *
     * The last value from the editor will be stored for later retrieval.
     */
    _hideEditor: function() {
        if (this._editor) {
            this._value = this._editor.getText();
            this._richTextDirty = false;
            this._editor.remove();
            this._editor = null;

            this.$el.empty();
        }
    }
}, {
    /*
     * Returns options used to display a TextEditorView in an inlineEditor.
     *
     * This will return an options dictionary that can be used with an
     * inlineEditor. The inlineEditor will make use of the TextEditorView
     * instead of a textarea.
     *
     * This can take options for the TextEditorView to change the default
     * behavior.
     */
    getInlineEditorOptions: function(options) {
        var textEditor;

        return {
            matchHeight: false,
            multiline: true,

            createMultilineField: function(editor) {
                var $editor = editor.element,
                    origRichText;

                textEditor = new RB.TextEditorView(options);
                textEditor.render();

                $editor.one('beginEdit', function() {
                    var $buttons = $editor.inlineEditor('buttons'),
                        $markdownRef,
                        $checkbox,
                        $span;

                    $span = $('<span/>')
                        .addClass('enable-markdown');

                    $checkbox = $('<input/>')
                        .attr({
                            id: _.uniqueId('markdown_check'),
                            type: 'checkbox'
                        })
                        .appendTo($span);
                    textEditor.bindRichTextCheckbox($checkbox);

                    $span.append($('<label/>')
                        .attr('for', $checkbox[0].id)
                        .text(gettext('Enable Markdown')));

                    $buttons.append($span);

                    $markdownRef = $('<a/>')
                        .addClass('markdown-info')
                        .attr({
                            href: MANUAL_URL + 'users/markdown/',
                            target: '_blank'
                        })
                        .text(gettext('Markdown Reference'))
                        .setVisible(textEditor.richText)
                        .appendTo($buttons);
                    textEditor.bindRichTextVisibility($markdownRef);
                });

                $editor.on('beginEdit', function() {
                    textEditor._showEditor();
                    origRichText = textEditor.richText;
                });

                $editor.on('cancel', function() {
                    textEditor._hideEditor();
                    textEditor.setRichText(origRichText);
                });

                $editor.on('complete', function() {
                    textEditor._hideEditor();
                });

                textEditor.$el.data('text-editor', textEditor);

                return textEditor.$el;
            },

            setFieldValue: function(editor, value) {
                textEditor.setText(value || '');
            },

            getFieldValue: function() {
                return textEditor.getText();
            },

            isFieldDirty: function(editor, initialValue) {
                return textEditor.isDirty(initialValue);
            }
        };
    },

    /*
     * Returns the TextEditorView for an inlineEditor element.
     */
    getFromInlineEditor: function($editor) {
        return $editor.inlineEditor('field').data('text-editor');
    }
});


})();
