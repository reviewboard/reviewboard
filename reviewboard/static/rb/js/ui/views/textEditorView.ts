import { BaseView, EventsHash, spina } from '@beanbag/spina';
import CodeMirror from 'codemirror';

import { UserSession } from 'reviewboard/common';

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
    static className = 'rb-c-text-editor__textarea -is-rich';

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

        const wrapperEl = this._codeMirror.getWrapperElement();
        wrapperEl.classList.add('rb-c-text-editor__textarea', '-is-rich');
        this.setElement(wrapperEl);

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
     * Set the cursor position within the editor.
     *
     * This uses client coordinates (which are relative to the viewport).
     *
     * Version Added:
     *     6.0
     *
     * Args:
     *     x (number):
     *         The client X coordinate to set.
     *
     *     y (number):
     *         The client Y coordinate to set.
     */
    setCursorPosition(
        x: number,
        y: number,
    ) {
        const codeMirror = this._codeMirror;

        codeMirror.setCursor(
            codeMirror.coordsChar(
                {
                    left: x,
                    top: y,
                },
                'window'));
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
    static className = 'rb-c-text-editor__textarea -is-plain';
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
     * Set the cursor position within the editor.
     *
     * This uses client coordinates (which are relative to the viewport).
     *
     * Setting the cursor position works in Firefox and WebKit/Blink-based
     * browsers. Not all browsers support the required APIs.
     *
     * Version Added:
     *     6.0
     *
     * Args:
     *     x (number):
     *         The client X coordinate to set.
     *
     *     y (number):
     *         The client Y coordinate to set.
     */
    setCursorPosition(
        x: number,
        y: number,
    ) {
        if (!document.caretPositionFromPoint &&
            !document.caretRangeFromPoint) {
            /*
             * We don't have what need to reliably return a caret position for
             * the text.
             *
             * There are tricks we can try in order to attempt to compute the
             * right position, based on line heights and character sizes, but
             * it gets more difficult with wrapping.
             *
             * In reality, both of the above methods are widespread enough to
             * rely upon, and if they don't exist, we just won't set the
             * cursor position.
             */
            return;
        }

        const $el = this.$el;
        const el = this.el;

        /*
         * We need a proxy element for both the Firefox and WebKit/Blink
         * implementations, because neither version works quite right with
         * a <textarea>.
         *
         * On Firefox, Document.caretPositionFromPoint will generally work
         * with a <textarea>, so long as you're clicking within a line. If
         * you click past the end of a line, however, you get a caret position
         * at the end of the <textarea>. Not ideal. This behavior doesn't
         * manifest for standard DOM nodes, so we can use a proxy here.
         *
         * On WebKit/Blink, Document.caretRangeFromPoint doesn't even work
         * with a <textarea> at all, so we're forced to use a proxy element
         * (See https://bugs.webkit.org/show_bug.cgi?id=30604).
         *
         * A second caveat here is that, in either case, we can't get a
         * position for off-screen elements (apparently). So we have to overlay
         * this exactly. We carefully align it and then use an opacity of 0 to
         * hide it,
         */
        const offset = $el.offset();
        const bounds = el.getBoundingClientRect();
        const $proxy = $('<pre>')
            .move(offset.left, offset.top, 'absolute')
            .css({
                'border': 0,
                'font': $el.css('font'),
                'height': `${bounds.height}px`,
                'line-height': $el.css('line-height'),
                'margin': 0,
                'opacity': 0,
                'padding': $el.css('padding'),
                'white-space': 'pre-wrap',
                'width': `${bounds.width}px`,
                'word-wrap': 'break-word',
                'z-index': 10000,
            })
            .text(this.el.value)
            .appendTo(document.body);

        let pos = null;

        if (document.caretPositionFromPoint) {
            /* Firefox */
            const caret = document.caretPositionFromPoint(x, y);

            if (caret) {
                pos = caret.offset;
            }
        } else if (document.caretRangeFromPoint) {
            /* Webkit/Blink. */
            const caret = document.caretRangeFromPoint(x, y);

            if (caret) {
                pos = caret.startOffset;
            }
        }

        $proxy.remove();

        if (pos !== null) {
            el.setSelectionRange(pos, pos);
        }
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
 * Options for the FormattingToolbarView.
 *
 * Version Added:
 *     6.0
 */
interface FormattingToolbarViewOptions {
    /** The CodeMirror wrapper object. */
    editor: CodeMirrorWrapper;
}


/**
 * Options for a group on the formatting toolbar.
 *
 * Version Added:
 *     6.0
 */
interface FormattingToolbarGroupOptions {
    /**
     * The unique ID of the group.
     */
    id: string;

    /**
     * The ARIA label to set for the group.
     */
    ariaLabel: string;

    /**
     * An optional list of item options to add to the group.
     */
    items?: FormattingToolbarItemOptions[];
}


/**
 * Options for an item on the formatting toolbar.
 *
 * Version Added:
 *     6.0
 */
interface FormattingToolbarItemOptions {
    /**
     * The unique ID of the item.
     */
    id: string;

    /**
     * An optional element to use instead of the default one.
     *
     * Callers should take care to ensure their elements are accessible.
     *
     * ``ariaLabel``, ``className``, and ``onClick`` are still applicable to
     * custom elements.
     */
    $el?: JQuery;

    /**
     * An optional ARIA label to set for the item.
     *
     * This is recommended.
     */
    ariaLabel?: string;

    /**
     * An extra CSS class name (or space-separated list of class names) to set.
     */
    className?: string;

    /**
     * Handler for when the button is clicked.
     */
    onClick?: (e: MouseEvent | JQuery.ClickEvent) => void;
}


/**
 * Information on an item group in the formatting toolbar.
 *
 * Version Added:
 *     6.0
 */
interface FormattingToolbarGroup {
    /**
     * The element for the group.
     */
    $el: JQuery;

    /**
     * The unique ID of the group.
     */
    id: string;

    /**
     * The mapping of item IDs to information in the group.
     */
    items: {
        [key: string]: FormattingToolbarItem
    };
}


/**
 * Information on an item in the formatting toolbar.
 *
 * Version Added:
 *     6.0
 */
interface FormattingToolbarItem {
    /**
     * The element for the item.
     */
    $el: JQuery;

    /**
     * The unique ID of the item.
     */
    id: string;
}


/**
 * The formatting toolbar for rich text fields.
 *
 * Version Added:
 *     6.0
 */
@spina
class FormattingToolbarView extends BaseView<
    Backbone.Model,
    HTMLDivElement,
    FormattingToolbarViewOptions
> {
    static className = 'rb-c-formatting-toolbar';

    /**********************
     * Instance variables *
     **********************/

    /**
     * A mapping of button group IDs to information.
     */
    buttonGroups: {
        [key: string]: FormattingToolbarGroup
    } = {};

    /**
     * The CodeMirror instance.
     */
    #codeMirror: CodeMirror;

    /**
     * The ID of the editor being managed.
     */
    #editorID: string;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (FormattingToolbarViewOptions):
     *         Options for the view.
     */
    initialize(options: FormattingToolbarViewOptions) {
        const editor = options.editor;
        const editorID = editor.el.id;

        console.assert(!!editorID);

        this.#codeMirror = editor._codeMirror;
        this.#editorID = editorID;

        this.addGroup({
            ariaLabel: _`Text formatting`,
            id: 'text',
            items: [
                {
                    ariaLabel: _`Bold`,
                    className: 'rb-c-formatting-toolbar__btn-bold',
                    id: 'bold',
                    onClick: this.#onBoldBtnClick.bind(this),
                },
                {
                    ariaLabel: _`Italic`,
                    className: 'rb-c-formatting-toolbar__btn-italic',
                    id: 'italic',
                    onClick: this.#onItalicBtnClick.bind(this),
                },
                {
                    ariaLabel: _`Strikethrough`,
                    className: 'rb-c-formatting-toolbar__btn-strikethrough',
                    id: 'strikethrough',
                    onClick: this.#onStrikethroughBtnClick.bind(this),
                },
                {
                    ariaLabel: _`Code literal`,
                    className: 'rb-c-formatting-toolbar__btn-code',
                    id: 'code',
                    onClick: this.#onCodeBtnClick.bind(this),
                },
            ],
        });

        this.addGroup({
            ariaLabel: _`Special formatting and media`,
            id: 'media',
            items: [
                {
                    ariaLabel: _`Insert link`,
                    className: 'rb-c-formatting-toolbar__btn-link',
                    id: 'link',
                    onClick: this.#onLinkBtnClick.bind(this),
                },
                {
                    $el: $(dedent`
                        <label class="rb-c-formatting-toolbar__btn"
                               aria-role="button" tabindex="0">
                        `)
                        .append(
                            $('<input type="file" style="display: none;">')
                                .on('change', this.#onImageUpload.bind(this))),
                    ariaLabel: _`Upload image`,
                    className: 'rb-c-formatting-toolbar__btn-image',
                    id: 'upload-image',
                },
            ],
        });

        this.addGroup({
            ariaLabel: _`Lists`,
            id: 'lists',
            items: [
                {
                    ariaLabel: _`Insert unordered list`,
                    className: 'rb-c-formatting-toolbar__btn-list-ul',
                    id: 'list-ul',
                    onClick: this.#onUListBtnClick.bind(this),
                },
                {
                    ariaLabel: _`Insert ordered list`,
                    className: 'rb-c-formatting-toolbar__btn-list-ol',
                    id: 'list-ol',
                    onClick: this.#onOListBtnClick.bind(this),
                },
            ],
        });
    }

    /**
     * Render the view.
     */
    onInitialRender() {
        this.$el.attr({
            'aria-controls': this.#editorID,
            'aria-label': _`Text formatting toolbar`,
            'role': 'toolbar',
        });
    }

    /**
     * Add a group on the toolbar for placing items.
     *
     * This may optionally take items to add to the group.
     *
     * Args:
     *     options (FormattingToolbarGroupOptions):
     *         Options for the group.
     */
    addGroup(options: FormattingToolbarGroupOptions) {
        const id = options.id;

        console.assert(!this.buttonGroups.hasOwnProperty(id),
                       `Toolbar group "${id}" was already registered.`);

        const $buttonGroup = $('<div>')
            .addClass('rb-c-formatting-toolbar__btn-group')
            .attr('aria-label', options.ariaLabel);

        const group: FormattingToolbarGroup = {
            $el: $buttonGroup,
            id: id,
            items: {},
        };

        this.buttonGroups[id] = group;

        if (options.items) {
            for (const item of options.items) {
                this.addItem(id, item);
            }
        }

        $buttonGroup.appendTo(this.$el);
    }

    /**
     * Add an item to a group.
     *
     * Args:
     *     groupID (string):
     *         The ID of the group to add to.
     *
     *     options (FormattingToolbarItemOptions):
     *         Options for the item to add.
     */
    addItem(
        groupID: string,
        options: FormattingToolbarItemOptions,
    ) {
        const group = this.buttonGroups[groupID];
        console.assert(!!group, `Toolbar group "${groupID}" does not exist.`);

        let $el = options.$el;

        if ($el === undefined) {
            $el = $('<button>')
                .attr({
                    'aria-pressed': 'false',
                    'class': 'rb-c-formatting-toolbar__btn',
                    'tabindex': '0',
                    'type': 'button',
                });
        }

        if (options.ariaLabel) {
            $el.attr({
                'aria-label': options.ariaLabel,
                'title': options.ariaLabel,
            });
        }

        if (options.className) {
            $el.addClass(options.className);
        }

        if (options.onClick) {
            $el.on('click', options.onClick);
        }

        $el.appendTo(group.$el);
    }

    /**
     * Handle a click on the "bold" button.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event object.
     */
    #onBoldBtnClick(e: JQuery.ClickEvent) {
        e.stopPropagation();
        e.preventDefault();

        this.#toggleInlineTextFormat(['**']);
    }

    /**
     * Handle a click on the "code" button.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event object.
     */
    #onCodeBtnClick(e: JQuery.ClickEvent) {
        e.stopPropagation();
        e.preventDefault();

        this.#toggleInlineTextFormat(['`']);
    }

    /**
     * Handle a click on the "italic" button.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event object.
     */
    #onItalicBtnClick(e: JQuery.ClickEvent) {
        e.stopPropagation();
        e.preventDefault();

        this.#toggleInlineTextFormat(['_', '*']);
    }

    /**
     * Handle a click on the "link" button.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event object.
     */
    #onLinkBtnClick(e: JQuery.ClickEvent) {
        e.stopPropagation();
        e.preventDefault();

        this.#toggleLinkSyntax();
    }

    /**
     * Handle an image upload from clicking the "image" button.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event object.
     */
    #onImageUpload(e: JQuery.ClickEvent) {
        const files = e.target.files;
        const token = this.#getCurrentTokenGroup()[0];

        this.#codeMirror.focus();
        this.#codeMirror.setCursor(token);

        if (files) {
            this.trigger('uploadImage', files[0]);
        }

        e.stopPropagation();
        e.preventDefault();
    }

    /**
     * Handle a click on the "ordered list" button.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event object.
     */
    #onOListBtnClick(e: JQuery.ClickEvent) {
        e.stopPropagation();
        e.preventDefault();

        this.#toggleListSyntax(true);
    }

    /**
     * Handle a click on the "strikethrough" button.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event object.
     */
    #onStrikethroughBtnClick(e: JQuery.ClickEvent) {
        e.stopPropagation();
        e.preventDefault();

        this.#toggleInlineTextFormat(['~~']);
    }

    /**
     * Handle a click on the "unordered list" button.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event object.
     */
    #onUListBtnClick(e: JQuery.ClickEvent) {
        e.stopPropagation();
        e.preventDefault();

        this.#toggleListSyntax(false);
    }

    /**
     * Toggle the state of the given inline text format.
     *
     * This toggles the syntax for inline markup such as bold, italic,
     * strikethrough, or code.
     *
     * Args:
     *     symbols (Array of string):
     *         The surrounding markup to add or remove.
     */
    #toggleInlineTextFormat(symbols: string[]) {
        const codeMirror = this.#codeMirror;
        const selection = codeMirror.getSelection();

        if (selection === '') {
            /*
             * If the syntax being toggled does not exist in the group where
             * the cursor is positioned, insert the syntax and position the
             * cursor between the inserted symbols. Otherwise, remove the
             * syntax.
             */
            const [groupStart, groupEnd] = this.#getCurrentTokenGroup();
            const range = codeMirror.getRange(groupStart, groupEnd);

            let wasReplaced = false;

            for (const sym of symbols) {
                if (range.startsWith(sym) && range.endsWith(sym)) {
                    const trimmedRange = this.#removeSyntax(range, sym);
                    codeMirror.replaceRange(trimmedRange, groupStart,
                                            groupEnd);
                    wasReplaced = true;
                    break;
                }
            }

            if (!wasReplaced) {
                const sym = symbols[0];

                codeMirror.replaceRange(`${sym}${range}${sym}`,
                                        groupStart, groupEnd);

                const cursor = codeMirror.getCursor();
                cursor.ch -= sym.length;
                codeMirror.setCursor(cursor);
            }
        } else {
            let wasReplaced = false;

            for (const sym of symbols) {
                if (selection.startsWith(sym) && selection.endsWith(sym)) {
                    /*
                     * The selection starts and ends with syntax matching the
                     * provided symbol, so remove them.
                     *
                     * For example: |**bold text**|
                     */
                    const newSelection = this.#removeSyntax(selection, sym);
                    codeMirror.replaceSelection(newSelection, 'around');
                    wasReplaced = true;
                    break;
                }
            }

            if (!wasReplaced) {
                /*
                 * There is an existing selection that may have syntax outside
                 * of it, so find the beginning and end of the entire token
                 * group, including both word and punctuation characters.
                 *
                 * For example: **|bold text|**
                 */
                const [groupStart, groupEnd] = this.#getCurrentTokenGroup();

                /* Update the selection for replacement. */
                codeMirror.setSelection(groupStart, groupEnd);
                const group = codeMirror.getSelection();

                for (const sym of symbols) {
                    if (group.startsWith(sym) && group.endsWith(sym)) {
                        const newGroup = this.#removeSyntax(group, sym);
                        codeMirror.replaceSelection(newGroup, 'around');
                        wasReplaced = true;
                        break;
                    }
                }

                if (!wasReplaced) {
                    /* The selection is not formatted, so add syntax. */
                    const sym = symbols[0];

                    /* Format each line of the selection. */
                    const lines = group.split('\n').map((line: string) => {
                        if (line === '') {
                            return line;
                        } else if (line.startsWith(sym) &&
                                   line.endsWith(sym)) {
                            /* Remove the formatting. */
                            return this.#removeSyntax(line, sym);
                        } else {
                            return `${sym}${line}${sym}`;
                        }
                    });

                    codeMirror.replaceSelection(lines.join('\n'), 'around');
                }
            }
        }

        codeMirror.focus();
    }

    /**
     * Return the current token group for the cursor/selection.
     *
     * This will find the surrounding text given the current user's cursor
     * position or selection.
     *
     * Returns:
     *     Array of number:
     *     A 2-element array containing the start and end position of the
     *     current token group.
     */
    #getCurrentTokenGroup(): number[] {
        const codeMirror = this.#codeMirror;
        const cursorStart = codeMirror.getCursor(true);
        const cursorEnd = codeMirror.getCursor(false);

        const groupStart = Object.assign({}, cursorStart);

        for (let curToken = codeMirror.getTokenAt(cursorStart, true);
             curToken.string !== ' ' && groupStart.ch !== 0;
             curToken = codeMirror.getTokenAt(groupStart, true)) {
            groupStart.ch -= 1;
        }

        const line = codeMirror.getLine(cursorStart.line);
        const lineLength = line.length;

        const groupEnd = Object.assign({}, cursorEnd);

        for (let curToken = codeMirror.getTokenAt(cursorEnd, true);
             curToken.string !== ' ' && groupEnd.ch < lineLength;
             curToken = codeMirror.getTokenAt(groupEnd, true)) {
            groupEnd.ch += 1;
        }

        if (groupEnd.ch !== lineLength && groupStart.line === groupEnd.line) {
            groupEnd.ch -= 1;
        }

        return [groupStart, groupEnd];
    }

    /**
     * Remove the given syntax from the provided text.
     *
     * Args:
     *     text (string):
     *         The text to edit.
     *
     *     sym (string):
     *         The markup to remove from the text.
     *
     * Returns:
     *     string:
     *     The text with the surrounding markup removed.
     */
    #removeSyntax(
        text: string,
        sym: string,
    ): string {
        let escapedSymbol;

        if (sym === '*') {
            escapedSymbol = '\\*';
        } else if (sym === '**') {
            escapedSymbol = '\\*\\*';
        } else {
            escapedSymbol = sym;
        }

        const regex = new RegExp(`^(${escapedSymbol})(.*)\\1$`, 'gm');

        return text.replace(regex, '$2');
    }

    /**
     * Toggle markdown list syntax for the current cursor position.
     *
     * Args:
     *     isOrderedList (boolean):
     *         ``true`` if toggling syntax for an ordered list, ``false`` for
     *         an unordered list.
     */
    #toggleListSyntax(isOrderedList: boolean) {
        const regex = isOrderedList ? /^[0-9]+\.\s/ : /^[\*|\+|-]\s/;
        const listSymbol = isOrderedList ? '1.' : '-';
        const codeMirror = this.#codeMirror;
        const cursor = codeMirror.getCursor();
        const line = codeMirror.getLine(cursor.line);
        const selection = codeMirror.getSelection();

        if (selection === '') {
            /*
             * If the list syntax being toggled exists on the current line,
             * remove it. Otherwise, add the syntax to the current line. In
             * both cases, preserve the relative cursor position if the line is
             * not empty.
             */
            if (regex.test(line)) {
                const newText = line.replace(regex, '');
                codeMirror.replaceRange(
                    newText,
                    { ch: 0, line: cursor.line },
                    { line: cursor.line });

                if (line) {
                    cursor.ch -= listSymbol.length + 1;
                    codeMirror.setCursor(cursor);
                }
            } else {
                codeMirror.replaceRange(
                    `${listSymbol} ${line}`,
                    { ch: 0, line: cursor.line },
                    { line: cursor.line });

                if (line) {
                    cursor.ch += listSymbol.length + 1;
                    codeMirror.setCursor(cursor);
                }
            }
        } else {
            if (regex.test(selection)) {
                const newText = selection.replace(regex, '');
                codeMirror.replaceSelection(newText, 'around');
            } else {
                const cursorStart = codeMirror.getCursor(true);
                const cursorEnd = codeMirror.getCursor(false);
                const precedingText = codeMirror.getLineTokens(cursor.line)
                    .filter(t => t.start < cursorStart.ch)
                    .reduce((acc, token) => acc + token.string, '');

                if (regex.test(precedingText)) {
                    /*
                     * There may be markup before theselection that needs to be
                     * removed, so extend the selection to be replaced if
                     * necessary.
                     */
                    const newText = selection.replace(regex, '');
                    codeMirror.setSelection({ ch: 0, line: cursor.line },
                                            cursorEnd);
                    codeMirror.replaceSelection(newText, 'around');
                } else {
                    /* The selection is not already formatted. Add syntax. */
                    codeMirror.replaceSelection(`${listSymbol} ${selection}`,
                                                'around');
                }
            }
        }

        codeMirror.focus();
    }

    /**
     * Toggle link syntax for the current cursor/selection.
     */
    #toggleLinkSyntax() {
        const regex = /\[(?<text>.*)\]\(.*\)/;
        const codeMirror = this.#codeMirror;
        const selection = codeMirror.getSelection();
        let cursor = codeMirror.getCursor();

        if (selection === '') {
            /*
             * If the group where the cursor is positioned is already a link,
             * remove the syntax. Otherwise, insert the syntax and position the
             * cursor where the text to be displayed will go.
             */
            const [groupStart, groupEnd] = this.#getCurrentTokenGroup();
            const range = codeMirror.getRange(groupStart, groupEnd);

            if (range === '') {
                /*
                 * If the group where the cursor is positioned is empty, insert
                 * the syntax and position the cursor where the text to display
                 * should go.
                 */
                codeMirror.replaceSelection(`[](url)`);
                codeMirror.setCursor(
                    CodeMirror.Pos(cursor.line, cursor.ch + 1));
            } else {
                const match = range.match(regex);

                if (match && match.groups) {
                    /*
                     * If there is a non-empty token group that is a formatted
                     * link, replace the syntax with the text.
                     */
                    const text = match.groups.text;
                    codeMirror.replaceRange(text, groupStart, groupEnd);
                } else {
                    /*
                     * Otherwise, insert the syntax using the token group as
                     * the text to display and position the selection where the
                     * URL will go.
                     */
                    codeMirror.replaceRange(`[${range}](url)`,
                                            groupStart, groupEnd);

                    cursor = codeMirror.getCursor();
                    codeMirror.setSelection(
                        CodeMirror.Pos(cursor.line, cursor.ch - 4),
                        CodeMirror.Pos(cursor.line, cursor.ch - 1));
                }
            }
        } else {
            let match = selection.match(regex);

            if (match && match.groups) {
                /*
                 * If the entire selection matches a formatted link, replace
                 * the selection with the text.
                 */
                codeMirror.replaceSelection(match.groups.text);
            } else {
                /*
                 * The selection may be part of a formatted link, so get the
                 * current token group to test against the regex and remove the
                 * syntax if it matches.
                 */
                const [groupStart, groupEnd] = this.#getCurrentTokenGroup();
                const range = codeMirror.getRange(groupStart, groupEnd);

                match = range.match(regex);

                if (match && match.groups) {
                    codeMirror.replaceRange(match.groups.text,
                                            groupStart, groupEnd);
                } else {
                    /*
                     * The selection is not already formatted, so insert the
                     * syntax using the current selection as the text to
                     * display, and position the selection where the URL will
                     * go.
                     */
                    codeMirror.replaceSelection(`[${selection}](url)`);

                    cursor = codeMirror.getCursor();
                    codeMirror.setSelection(
                        CodeMirror.Pos(cursor.line, cursor.ch - 4),
                        CodeMirror.Pos(cursor.line, cursor.ch - 1));
                }
            }
        }
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
    static className = 'rb-c-text-editor';

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

    /**
     * The markdown formatting toolbar view.
     *
     * Version Added:
     *     6.0
     */
    #formattingToolbar: FormattingToolbarView = null;

    /** The saved previous height, used to trigger the resize event . */
    #prevClientHeight: number = null;

    /** Whether the rich text state is unsaved. */
    #richTextDirty = false;

    /**
     * The cursor position to set when starting edit mode.
     *
     * Version Added:
     *     6.0
     */
    #startCursorPos: [number, number] = null;

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
     * Set the cursor position within the editor.
     *
     * This uses client coordinates (which are relative to the viewport).
     *
     * Version Added:
     *     6.0
     *
     * Args:
     *     x (number):
     *         The client X coordinate to set.
     *
     *     y (number):
     *         The client Y coordinate to set.
     */
    setCursorPosition(
        x: number,
        y: number,
    ) {
        if (this._editor) {
            this._editor.setCursorPosition(x, y);
        } else {
            this.#startCursorPos = [x, y];
        }
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
            if (this.#formattingToolbar !== null) {
                height -= this.#formattingToolbar.$el.outerHeight(true);
            }

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
        if (this.richText) {
            DnDUploader.instance.registerDropTarget(
                this.$el, _`Drop to add an image`,
                this._uploadImage.bind(this));

            this._editor = new CodeMirrorWrapper({
                autoSize: this.options.autoSize,
                minHeight: this.options.minHeight,
                parentEl: this.el,
            });
            this._editor.el.id = _.uniqueId('rb-c-text-editor_');

            this.#formattingToolbar = new FormattingToolbarView({
                _uploadImage: this._uploadImage.bind(this),
                editor: this._editor,
            });
            this.#formattingToolbar.renderInto(this.$el);
            this.listenTo(this.#formattingToolbar, 'uploadImage',
                          this._uploadImage);

        } else {
            this._editor = new TextAreaWrapper({
                autoSize: this.options.autoSize,
                minHeight: this.options.minHeight,
                parentEl: this.el,
            });
        }

        this._editor.setText(this.#value);

        const startCursorPos = this.#startCursorPos;

        if (startCursorPos !== null) {
            this._editor.setCursorPosition(startCursorPos[0],
                                           startCursorPos[1]);
        }

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

        if (this.#formattingToolbar) {
            this.#formattingToolbar.remove();
            this.#formattingToolbar = null;
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
