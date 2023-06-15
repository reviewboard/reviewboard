import { BaseView, EventsHash, spina } from '@beanbag/spina';
import CodeMirror from 'codemirror';

import { UserSession } from 'reviewboard/common/models/userSession';

import { DnDUploader } from './dndUploaderView';


/*
 * Define a CodeMirror mode we can plug in as the default below.
 *
 * This mode won't have any special highlighting, but will avoid the Markdown
 * mode's default behavior of rendering "plain/text" code (the default) the
 * same way as literal code, which we really want to avoid.
 */
CodeMirror.defineSimpleMode('rb-text-plain', {
    start: [
        {
            next: 'start',
            regex: /.*/,
            token: 'rb-cm-codeblock-plain',
        },
    ],
});

CodeMirror.defineMIME('text/plain', 'rb-text-plain');


/**
 * Options for the editor wrapper views.
 *
 * Version Added:
 *     6.0
 */
interface EditorWrapperOptions {
    /**
     * Whether the editor should automatically resize to fit its container.
     */
    autoSize?: boolean;

    /**
     * The minimum vertical size of the editor.
     */
    minHeight?: number;

    /**
     * The parent element for the editor.
     */
    parentEl?: Element;
}


/**
 * Wraps CodeMirror, providing a standard interface for TextEditorView's usage.
 */
@spina
class CodeMirrorWrapper extends BaseView<
    Backbone.Model,
    HTMLDivElement,
    EditorWrapperOptions
> {
    /**********************
     * Instance variables *
     **********************/

    _codeMirror: CodeMirror;

    /**
     * Initialize CodeMirrorWrapper.
     *
     * This will set up CodeMirror based on the objects, add it to the parent,
     * and begin listening to events.
     *
     * Args:
     *     options (EditorWrapperOptions):
     *         Options for the wrapper.
     */
    initialize(options: EditorWrapperOptions) {
        const codeMirrorOptions = {
            electricChars: false,
            extraKeys: {
                'End': 'goLineRight',
                'Enter': 'newlineAndIndentContinueMarkdownList',
                'Home': 'goLineLeft',
                'Shift-Tab': false,
                'Tab': false,
            },
            lineWrapping: true,
            mode: {
                highlightFormatting: true,
                name: 'gfm',

                /*
                 * The following token type overrides will be prefixed with
                 * ``cm-`` when used as classes.
                 */
                tokenTypeOverrides: {
                    code: 'rb-markdown-code',
                    list1: 'rb-markdown-list1',
                    list2: 'rb-markdown-list2',
                    list3: 'rb-markdown-list3',
                },
            },
            styleSelectedText: true,
            theme: 'rb default',
            viewportMargin: options.autoSize ? Infinity : 10,
        };

        this._codeMirror = new CodeMirror(options.parentEl,
                                          codeMirrorOptions);

        this.setElement(this._codeMirror.getWrapperElement());

        if (options.minHeight !== undefined) {
            this.$el.css('min-height', options.minHeight);
        }

        this._codeMirror.on('viewportChange',
                            () => this.$el.triggerHandler('resize'));
        this._codeMirror.on('change', () => this.trigger('change'));
    }

    /**
     * Return whether or not the editor's contents have changed.
     *
     * Args:
     *     initialValue (string):
     *         The initial value of the editor.
     *
     * Returns:
     *     boolean:
     *     Whether or not the editor is dirty.
     */
    isDirty(
        initialValue: string,
    ): boolean {
        /*
         * We cannot trust codeMirror's isClean() method.
         *
         * It is also possible for initialValue to be undefined, so we use an
         * empty string in that case instead.
         */
        return (initialValue || '') !== this.getText();
    }

    /**
     * Set the text in the editor.
     *
     * Args:
     *     text (string):
     *         The new text for the editor.
     */
    setText(text: string) {
        this._codeMirror.setValue(text);
    }

    /**
     * Return the text in the editor.
     *
     * Returns:
     *     string:
     *     The current contents of the editor.
     */
    getText(): string {
        return this._codeMirror.getValue();
    }

    /**
     * Insert a new line of text into the editor.
     *
     * If the editor has focus, insert at the cursor position. Otherwise,
     * insert at the end.
     *
     * Args:
     *     text (string):
     *         The text to insert.
     */
    insertLine(text: string) {
        let position;

        if (this._codeMirror.hasFocus()) {
            const cursor = this._codeMirror.getCursor();
            const line = this._codeMirror.getLine(cursor.line);
            position = CodeMirror.Pos(cursor.line, line.length - 1);

            if (line.length !== 0) {
                /*
                 * If the current line has some content, insert the new text on
                 * the line after it.
                 */
                text = '\n' + text;
            }

            if (!text.endsWith('\n')) {
                text += '\n';
            }
        } else {
            position = CodeMirror.Pos(this._codeMirror.lastLine());
            text = '\n' + text;
        }

        this._codeMirror.replaceRange(text, position);
    }

    /**
     * Return the full client height of the content.
     *
     * Returns:
     *     number:
     *     The client height of the editor.
     */
    getClientHeight(): number {
        return this._codeMirror.getScrollInfo().clientHeight;
    }

    /**
     * Set the size of the editor.
     *
     * Args:
     *     width (number):
     *         The new width of the editor.
     *
     *     height (number):
     *         The new height of the editor.
     */
    setSize(
        width: number,
        height: number,
    ) {
        this._codeMirror.setSize(width, height);
        this._codeMirror.refresh();
    }

    /**
     * Focus the editor.
     */
    focus() {
        this._codeMirror.focus();
    }
}


/**
 * Wraps <textarea>, providing a standard interface for TextEditorView's usage.
 */
@spina
class TextAreaWrapper extends BaseView<
    Backbone.Model,
    HTMLTextAreaElement,
    EditorWrapperOptions
> {
    static tagName = 'textarea';

    /**********************
     * Instance variables *
     **********************/

    options: EditorWrapperOptions;

    /*
     * Initialize TextAreaWrapper.
     *
     * This will set up the element based on the provided options, begin
     * listening for events, and add the element to the parent.
     *
     * Args:
     *     options (EditorWrapperOptions):
     *         Options for the wrapper.
     */
    initialize(options: EditorWrapperOptions) {
        this.options = options;

        if (options.autoSize) {
            this.$el.autoSizeTextArea();
        }

        this.$el
            .css('width', '100%')
            .appendTo(options.parentEl)
            .on('change keydown keyup keypress', () => this.trigger('change'));

        if (options.minHeight !== undefined) {
            if (options.autoSize) {
                this.$el.autoSizeTextArea('setMinHeight',
                                          options.minHeight);
            } else {
                this.$el.css('min-height', this.options.minHeight);
            }
        }
    }

    /**
     * Return whether or not the editor's contents have changed.
     *
     * Args:
     *     initialValue (string):
     *         The initial value of the editor.
     *
     * Returns:
     *     boolean:
     *     Whether or not the editor is dirty.
     */
    isDirty(
        initialValue: string,
    ): boolean {
        const value = this.el.value || '';

        return value.length !== initialValue.length ||
               value !== initialValue;
    }

    /**
     * Set the text in the editor.
     *
     * Args:
     *     text (string):
     *         The new text for the editor.
     */
    setText(text: string) {
        this.el.value = text;

        if (this.options.autoSize) {
            this.$el.autoSizeTextArea('autoSize');
        }
    }

    /**
     * Return the text in the editor.
     *
     * Returns:
     *     string:
     *     The current contents of the editor.
     */
    getText(): string {
        return this.el.value;
    }

    /**
     * Insert a new line of text into the editor.
     *
     * Args:
     *     text (string):
     *         The text to insert.
     */
    insertLine(text: string) {
        if (this.$el.is(':focus')) {
            const value = this.el.value;
            const cursor = this.el.selectionEnd;
            const endOfLine = value.indexOf('\n', cursor);

            if (endOfLine === -1) {
                // The cursor is on the last line.
                this.el.value += '\n' + text;
            } else {
                // The cursor is in the middle of the text.
                this.el.value = (value.slice(0, endOfLine + 1) + '\n' + text +
                                 '\n' + value.slice(endOfLine));
            }
        } else {
            this.el.value += '\n' + text;
        }
    }

    /**
     * Return the full client height of the content.
     *
     * Returns:
     *     number:
     *     The client height of the editor.
     */
    getClientHeight(): number {
        return this.el.clientHeight;
    }

    /**
     * Set the size of the editor.
     *
     * Args:
     *     width (number):
     *         The new width of the editor.
     *
     *     height (number):
     *         The new height of the editor.
     */
    setSize(
        width: number | string,
        height: number | string,
    ) {
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
    }

    /**
     * Focus the editor.
     */
    focus() {
        this.el.focus();
    }
}


/**
 * Options for the TextEditorView.
 *
 * Version Added:
 *     6.0
 */
export interface TextEditorViewOptions {
    /**
     * Whether the editor should automatically resize to fit its container.
     */
    autoSize?: boolean;

    /**
     * Definitions of a model attribute to use to bind the "richText" value to.
     */
    bindRichText?: {
        attrName: string;
        model: Backbone.Model;
    };

    /**
     * The minimum vertical size of the editor.
     */
    minHeight?: number;

    /**
     * Whether the editor is using rich text (Markdown).
     */
    richText?: boolean;

    /**
     * The initial text.
     */
    text?: string;
}


/**
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
@spina
export class TextEditorView extends BaseView<
    Backbone.Model,
    HTMLDivElement,
    TextEditorViewOptions
> {
    static className = 'text-editor';

    static defaultOptions: Partial<TextEditorViewOptions> = {
        autoSize: true,
        minHeight: 70,
    };

    static events: EventsHash ={
        'focus': 'focus',
        'remove': '_onRemove',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The view options. */
    options: TextEditorViewOptions;

    /** Whether the editor is using rich text. */
    richText: boolean;

    /** The saved previous height, used to trigger the resize event . */
    #prevClientHeight: number = null;

    /** Whether the rich text state is unsaved. */
    #richTextDirty = false;

    /** The current value of the editor. */
    #value: string;

    /** The editor wrapper. */
    _editor: CodeMirrorWrapper | TextAreaWrapper;

    /**
     * Initialize the view with any provided options.
     *
     * Args:
     *     options (TextEditorViewOptions, optional):
     *         Options for view construction.
     */
    initialize(options: TextEditorViewOptions = {}) {
        this._editor = null;
        this.#prevClientHeight = null;

        this.options = _.defaults(options, TextEditorView.defaultOptions);
        this.richText = !!this.options.richText;
        this.#value = this.options.text || '';
        this.#richTextDirty = false;

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
        if (UserSession.instance.get('defaultUseRichText')) {
            this.setRichText(true);
        }
    }

    /**
     * Render the text editor.
     *
     * This will set the class name on the element, ensuring we have a
     * standard set of styles, even if this editor is bound to an existing
     * element.
     */
    onInitialRender() {
        this.$el.addClass(this.className);
    }

    /**
     * Set whether or not rich text (Markdown) is to be used.
     *
     * This can dynamically change the text editor to work in plain text
     * or Markdown.
     *
     * Args:
     *     richText (boolean):
     *         Whether the editor should use rich text.
     */
    setRichText(richText: boolean) {
        if (richText === this.richText) {
            return;
        }

        if (this._editor) {
            this.hideEditor();
            this.richText = richText;
            this.showEditor();

            this.#richTextDirty = true;

            this.$el.triggerHandler('resize');
        } else {
            this.richText = richText;
        }

        this.trigger('change:richText', richText);
        this.trigger('change');
    }

    /**
     * Bind a richText attribute on a model to the mode on this editor.
     *
     * This editor's richText setting will stay in sync with the attribute
     * on the given mode.
     *
     * Args:
     *     model (Backbone.Model):
     *         A model to bind to.
     *
     *     attrName (string):
     *         The name of the attribute to bind.
     */
    bindRichTextAttr(
        model: Backbone.Model,
        attrName: string,
    ) {
        this.setRichText(model.get(attrName));

        this.listenTo(model, `change:${attrName}`,
                      (model, value) => this.setRichText(value));
    }

    /**
     * Bind an Enable Markdown checkbox to this text editor.
     *
     * The checkbox will initially be set to the value of the editor's
     * richText property. Toggling the checkbox will then manipulate that
     * property.
     *
     * Args:
     *     $checkbox (jQuery):
     *         The checkbox to bind.
     */
    bindRichTextCheckbox($checkbox: JQuery) {
        $checkbox
            .prop('checked', this.richText)
            .on('change', () => this.setRichText($checkbox.prop('checked')));

        this.on('change:richText',
                () => $checkbox.prop('checked', this.richText));
    }

    /**
     * Bind the visibility of an element to the richText property.
     *
     * If richText ist true, the element will be shown. Otherwise, it
     * will be hidden.
     *
     * Args:
     *     $el (jQuery):
     *         The element to show when richText is true.
     */
    bindRichTextVisibility($el: JQuery) {
        $el.toggle(this.richText);

        this.on('change:richText', () => $el.toggle(this.richText));
    }

    /**
     * Return whether or not the editor's contents have changed.
     *
     * Args:
     *     initialValue (string):
     *         The initial value of the editor.
     *
     * Returns:
     *     boolean:
     *     Whether or not the editor is dirty.
     */
    isDirty(
        initialValue: string,
    ): boolean {
        return this._editor !== null &&
               (this.#richTextDirty ||
                this._editor.isDirty(initialValue || ''));
    }

    /**
     * Set the text in the editor.
     *
     * Args:
     *     text (string):
     *         The new text for the editor.
     */
    setText(text: string) {
        if (text !== this.getText()) {
            if (this._editor) {
                this._editor.setText(text);
            } else {
                this.#value = text;
            }
        }

        this.trigger('change');
    }

    /**
     * Return the text in the editor.
     *
     * Returns:
     *     string:
     *     The current contents of the editor.
     */
    getText(): string {
        return this._editor ? this._editor.getText() : this.#value;
    }

    /**
     * Insert a new line of text into the editor.
     *
     * Args:
     *     text (string):
     *         The text to insert.
     */
    insertLine(text: string) {
        if (this._editor) {
            this._editor.insertLine(text);
        } else {
            if (this.#value.endsWith('\n')) {
                this.#value += text + '\n';
            } else {
                this.#value += '\n' + text;
            }
        }

        this.trigger('change');
    }

    /**
     * Set the size of the editor.
     *
     * Args:
     *     width (number):
     *         The new width of the editor.
     *
     *     height (number):
     *         The new height of the editor.
     */
    setSize(
        width: number,
        height: number,
    ) {
        if (this._editor) {
            this._editor.setSize(width, height);
        }
    }

    /**
     * Show the editor.
     *
     * Returns:
     *     TextEditorView:
     *     This object, for chaining.
     */
    show(): this {
        this.$el.show();
        this.showEditor();

        return this;
    }

    /**
     * Hide the editor.
     *
     * Returns:
     *     TextEditorView:
     *     This object, for chaining.
     */
    hide(): this {
        this.hideEditor();
        this.$el.hide();

        return this;
    }

    /**
     * Focus the editor.
     */
    focus() {
        if (this._editor) {
            this._editor.focus();
        }
    }

    /**
     * Handler for the remove event.
     *
     * Disables the drag-and-drop overlay.
     */
    private _onRemove() {
        DnDUploader.instance.unregisterDropTarget(this.$el);
    }

    /**
     * Show the actual editor wrapper.
     *
     * Any stored text will be transferred to the editor, and the editor
     * will take control over all operations.
     */
    showEditor() {
        const EditorCls = this.richText ? CodeMirrorWrapper : TextAreaWrapper;

        if (this.richText) {
            DnDUploader.instance.registerDropTarget(
                this.$el, _`Drop to add an image`,
                this._uploadImage.bind(this));
        }

        this._editor = new EditorCls({
            autoSize: this.options.autoSize,
            minHeight: this.options.minHeight,
            parentEl: this.el,
        });

        this._editor.setText(this.#value);
        this.#value = '';
        this.#richTextDirty = false;
        this.#prevClientHeight = null;

        this._editor.$el.on(
            'resize',
            _.throttle(() => this.$el.triggerHandler('resize'), 250));

        this.listenTo(this._editor, 'change', _.throttle(() => {
            /*
             * Make sure that the editor wasn't closed before the throttled
             * handler was reached.
             */
            if (this._editor === null) {
                return;
            }

            const clientHeight = this._editor.getClientHeight();

            if (clientHeight !== this.#prevClientHeight) {
                this.#prevClientHeight = clientHeight;
                this.$el.triggerHandler('resize');
            }

            this.trigger('change');
        }, 500));

        this.focus();
    }

    /**
     * Hide the actual editor wrapper.
     *
     * The last value from the editor will be stored for later retrieval.
     */
    hideEditor() {
        DnDUploader.instance.unregisterDropTarget(this.$el);

        if (this._editor) {
            this.#value = this._editor.getText();
            this.#richTextDirty = false;

            this._editor.remove();
            this._editor = null;

            this.$el.empty();
        }
    }

    /**
     * Return whether or not a given file is an image.
     *
     * Args:
     *     file (File):
     *         The file to check.
     *
     * Returns:
     *     boolean:
     *     True if the given file appears to be an image.
     */
    private _isImage(
        file: File,
    ): boolean {
        if (file.type) {
            return (file.type.split('/')[0] === 'image');
        }

        const filename = file.name.toLowerCase();

        return ['.jpeg', '.jpg', '.png', '.gif', '.bmp', '.tiff', '.svg'].some(
            extension => filename.endsWith(extension));
    }

    /**
     * Upload the image and append an image link to the editor's contents.
     *
     * Creates an instance of UserFileAttachment and saves it without the file,
     * then updates the model with the file. This allows the file to be
     * uploaded asynchronously after we get the link that is generated when the
     * UserFileAttachment is created.
     *
     * Args:
     *     file (File):
     *         The image file to upload.
     */
    private _uploadImage(file: File) {
        if (!this._isImage(file)) {
            return;
        }

        const userFileAttachment = new RB.UserFileAttachment({
            caption: file.name,
        });

        userFileAttachment.save()
            .then(() => {
                this.insertLine(
                    `![Image](${userFileAttachment.get('downloadURL')})`);

                userFileAttachment.set('file', file);
                userFileAttachment.save()
                    .catch(err => alert(err.message));
            })
            .catch(err => alert(err.message));
    }
}
