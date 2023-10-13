/** View classes for various types of inline editors. */

import { BaseView, spina } from '@beanbag/spina';

import { TextEditorView, TextEditorViewOptions } from './textEditorView';


interface InlineEditorViewOptions {
    /** The duration of animated transitions, in milliseconds. */
    animationSpeedMS: number;

    /**
     * Whether to defer event setup after rendering.
     *
     * This should be used when a consumer wants to prioritize event handling
     * (such as handling the "enter" key for autocomplete).
     */
    deferEventSetup: boolean;

    /**
     * The maximum mouse pixel movement allowed before going into edit mode.
     *
     * This is the most the mouse cursor can move in any direction between a
     * mousedown and a mouseup event while still enabling going into edit
     * mode. Any more movement may indicate an attempt to select text or drag
     * a link/image, and should not trigger edit mode.
     *
     * We default this to 3, which allows for a little bit of movement from the
     * action of pressing down on a mouse or trackpad.
     *
     * Version Added:
     *     6.0
     */
    editDragThreshold: number;

    /**
     * The class name to use for the edit icon.
     *
     * This is only used if ``editIconPath`` is unspecified.
     */
    editIconClass: string;

    /** The path for an image for the edit icon. */
    editIconPath: string;

    /** Whether editing is enabled. */
    enabled: boolean;

    /** Extra height to add when displaying the editor, in pixels. */
    extraHeight: number;

    /**
     * The label of the field, used for accessibility purposes.
     *
     * Version Added:
     *     6.0
     */
    fieldLabel: string;

    /** Whether to focus the field when opening the editor. */
    focusOnOpen: boolean;

    /**
     * A function to format the resulting value.
     *
     * After the value is saved, this function can transform it for display
     * into the HTML element.
     */
    formatResult: (unknown) => string;

    /** The class to add to the form's DOM element. */
    formClass: string;

    /** A function to retrieve the field value. */
    getFieldValue: (InlineEditorView) => unknown;

    /**
     * Whether the field has a "raw value".
     *
     * If this is ``true``, it means that there is data for the field separate
     * from the actual contents of the element.
     */
    hasRawValue: boolean;

    /**
     * Whether the button's icons should be short (icons only).
     *
     * This should be used when space is limited and the Save/Cancel buttons
     * need to be of minimal size.
     *
     * Version Added:
     *     6.0
     */
    hasShortButtons: boolean;

    /** A function to calculate whether the editor value is dirty. */
    isFieldDirty: (InlineEditorView, unknown) => boolean;

    /**
     * Whether to attempt to match the editor height to the replaced element.
     */
    matchHeight: boolean;

    /** Whether the text input should be multi-line or single-line. */
    multiline: boolean;

    /**
     * Whether to trigger a ``complete`` event even if the value is unchanged.
     *
     * If this is ``false``, the editor will trigger a ``cancel`` event
     * instead.
     */
    notifyUnchangedCompletion: boolean;

    /** Whether to prompt the user before cancelling if the editor is dirty. */
    promptOnCancel: boolean;

    /**
     * The data of the raw value.
     *
     * This is only used if ``hasRawValue`` is ``true``.
     */
    rawValue: unknown;

    /** A function to set the field value. */
    setFieldValue: (InlineEditorView, unknown) => void;

    /** Whether to show OK/Cancel buttons. */
    showButtons: boolean;

    /** Whether to show the edit icon. */
    showEditIcon: boolean;

    /** Whether to show the required flag on the edit icon. */
    showRequiredFlag: boolean;

    /** Whether the editor should be open when first created. */
    startOpen: boolean;

    /** Whether to strip out HTML tags when normalizing input. */
    stripTags: boolean;

    /**
     * Whether the editor can be opened only by clicking the edit icon.
     *
     * If this is ``true``, the only way to start an edit is by clicking the
     * edit icon. If this is ``false``, clicking on the value will also
     * trigger an edit.
     */
    useEditIconOnly: boolean;
}


interface EditOptions {
    /** Whether to suppress animation. */
    preventAnimation?: boolean;

    /**
     * The client X coordinate of a mouse click triggering edit mode.
     *
     * Version Added:
     *     6.0
     */
    clickX?: number;

    /**
     * The client Y coordinate of a mouse click triggering edit mode.
     *
     * Version Added:
     *     6.0
     */
    clickY?: number;
}


interface SaveOptions {
    /** Whether to suppress event triggers. */
    preventEvents?: boolean;
}


/**
 * A view for inline editors.
 *
 * This provides the framework for items which are "editable". These provide a
 * way to switch between a normal view and an edit view, which is usually a
 * text box (either single- or multiple-line).
 */
@spina({
    prototypeAttrs: ['defaultOptions'],
})
export class InlineEditorView<
    TModel extends Backbone.Model = undefined,
    TElement extends HTMLElement = HTMLDivElement,
    TExtraViewOptions extends InlineEditorViewOptions = InlineEditorViewOptions
> extends BaseView<TModel, TElement, TExtraViewOptions> {
    /**
     * Defaults for the view options.
     */
    static defaultOptions: Partial<InlineEditorViewOptions> = {
        animationSpeedMS: 200,
        deferEventSetup: false,
        editDragThreshold: 3,
        editIconClass: null,
        editIconPath: null,
        enabled: true,
        extraHeight: 100,
        fieldLabel: null,
        focusOnOpen: true,
        formClass: '',
        formatResult: value => value.htmlEncode(),
        getFieldValue: editor => editor.$field.val(),
        hasRawValue: false,
        isFieldDirty: (editor, initialValue) => {
            const value = editor.getValue() || '';
            const normValue = (editor.options.hasRawValue
                               ? value
                               : value.htmlEncode()) || '';
            initialValue = editor.normalizeText(initialValue);

            return (normValue.length !== initialValue.length ||
                    normValue !== initialValue);
        },
        matchHeight: true,
        multiline: false,
        notifyUnchangedCompletion: false,
        promptOnCancel: true,
        rawValue: null,
        setFieldValue: (editor, value) => editor.$field.val(value),
        showButtons: true,
        showEditIcon: true,
        showRequiredFlag: false,
        startOpen: false,
    };

    /**********************
     * Instance variables *
     **********************/

    $buttons: JQuery;

    /**
     * The field used to edit the caption.
     */
    $field: JQuery;

    options: TExtraViewOptions;
    _$editIcon: JQuery;

    /**
     * The wrapper for the edit field.
     *
     * Version Added:
     *     6.0
     */
    _$fieldWrapper: JQuery;

    _$form: JQuery;
    _dirty = false;
    _dirtyCalcTimeout: number = null;
    _editing = false;
    _initialValue: unknown = null;
    _isTextArea: boolean;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (InlineEditorViewOptions):
     *         Options for the view.
     */
    initialize(options: Partial<TExtraViewOptions>) {
        this.options = _.defaults(options, this.defaultOptions);
    }

    /**
     * Render the view.
     */
    onInitialRender() {
        const options = this.options;
        const multiline = options.multiline;
        const fieldLabel = options.fieldLabel;
        const editorID = _.uniqueId('rb-c-inline-editor');

        this.$el.data('inline-editor', this);

        const $form = $('<form>')
            .addClass('rb-c-inline-editor')
            .addClass(multiline ? '-is-multi-line'
                                : '-is-single-line')
            .attr({
                'aria-label': fieldLabel
                              ? _`Edit the ${fieldLabel} field`
                              : _`Edit the field`,
                'id': editorID,
            });

        if (options.formClass) {
            $form.addClass(options.formClass);
        }

        if (options.hasShortButtons) {
            $form.addClass('-has-short-buttons');
        }

        this._$form = $form;

        const $fieldWrapper = $('<div class="rb-c-inline-editor__field"/>')
            .appendTo($form);
        this._$fieldWrapper = $fieldWrapper;

        this.$field = this.createField()
            .appendTo($fieldWrapper);
        this._isTextArea = (this.$field[0].tagName === 'TEXTAREA');

        this.$buttons = $();

        if (options.showButtons) {
            this.$buttons = $('<div>')
                .hide()
                .addClass('rb-c-inline-editor__actions')
                .appendTo($form);

            $('<button class="rb-c-button" data-action="save">')
                .append($('<span class="rb-c-button__icon">')
                    .attr('aria-hidden', 'true'))
                .append($('<label class="rb-c-button__label">')
                    .text(_`Save`))
                .attr('aria-label',
                      fieldLabel
                      ? _`Save ${fieldLabel}`
                      : _`Save the field`)
                .appendTo(this.$buttons)
                .click(e => {
                    e.preventDefault();
                    e.stopPropagation();

                    this.submit();
                });

            $('<button class="rb-c-button" data-action="cancel">')
                .append($('<span class="rb-c-button__icon">')
                    .attr('aria-hidden', 'true'))
                .append($('<label class="rb-c-button__label">')
                    .text(_`Cancel`))
                .attr('aria-label',
                      fieldLabel
                      ? _`Cancel editing ${fieldLabel} and discard changes`
                      : _`Cancel editing and discard changes`)
                .appendTo(this.$buttons)
                .click(e => {
                    e.preventDefault();
                    e.stopPropagation();

                    this.cancel();
                });
        }

        this._$editIcon = $();

        if (options.showEditIcon) {
            const editText = fieldLabel
                             ? _`Edit the ${fieldLabel} field`
                             : _`Edit this field`;

            this._$editIcon = $('<a href="#" role="button">')
                .addClass('rb-c-inline-editor-edit-icon')
                .attr({
                    'aria-controls': editorID,
                    'aria-label': editText,
                    'tabindex': 0,
                    'title': editText,
                })
                .click(e => {
                    e.preventDefault();
                    e.stopPropagation();

                    this.startEdit();
                });

            if (options.editIconPath) {
                this._$editIcon.append(
                    `<img src="${options.editIconPath}">`);
            } else if (options.editIconClass) {
                this._$editIcon.append(
                    `<div class="${options.editIconClass}" aria-hidden="true"></div>`);
            }

            if (options.showRequiredFlag) {
                const requiredText = _`This field is required`;
                $('<span class="required-flag">*</span>')
                    .attr({
                        'aria-label': requiredText,
                        'title': requiredText,
                    })
                    .appendTo(this._$editIcon);
            }

            if (multiline && this.$el[0].id) {
                $(`label[for="${this.$el[0].id}"]`)
                    .append(this._$editIcon);
            } else {
                this._$editIcon.insertAfter(this.$el);
            }
        }

        $form
            .hide()
            .insertBefore(this.$el);

        if (!options.deferEventSetup) {
            this.setupEvents();
        }

        if (options.startOpen) {
            this.startEdit({
                preventAnimation: true,
            });
        }

        if (options.enabled) {
            this.enable();
        } else {
            this.disable();
        }
    }

    /**
     * Create and return the field to use for the input element.
     *
     * Returns:
     *     jQuery:
     *     The newly created input element.
     */
    createField(): JQuery {
        if (this.options.multiline) {
            return $('<textarea>').autoSizeTextArea();
        } else {
            return $('<input type="text">');
        }
    }

    /**
     * Remove the view.
     *
     * Returns:
     *     InlineEditorView:
     *     This object, for chaining.
     */
    remove(): this {
        super.remove();

        $(window).off(this.cid);

        return this;
    }

    /**
     * Connect events.
     */
    setupEvents() {
        const options = this.options;

        this.$field
            .keydown(e => {
                e.stopPropagation();

                if (e.key === 'Enter') {
                    if (!options.multiline || e.ctrlKey) {
                        this.submit();
                    }

                    if (!options.multiline) {
                        e.preventDefault();
                    }
                } else if (e.key === 'Escape') {
                    this.cancel();
                } else if (e.key === 's' || e.key === 'S') {
                    if (e.ctrlKey) {
                        this.submit();
                        e.preventDefault();
                    }
                }
            })
            .keypress(e => e.stopPropagation())
            .keyup(e => {
                e.stopPropagation();
                e.preventDefault();

                this._scheduleUpdateDirtyState();
            })
            .on('cut paste', () => this._scheduleUpdateDirtyState());

        if (!options.useEditIconOnly) {
            /*
             * Check if the mouse was dragging, so that the editor isn't opened
             * when text is selected.
             */
            let lastX: number = null;
            let lastY: number = null;
            let isDragging = true;

            this.$el
                .on('click', 'a', e => e.stopPropagation())
                .click(e => {
                    e.stopPropagation();
                    e.preventDefault();

                    if (!isDragging) {
                        this.startEdit({
                            clickX: e.clientX,
                            clickY: e.clientY,
                        });
                    }

                    isDragging = true;
                })
                .mousedown(e => {
                    isDragging = false;
                    lastX = e.clientX;
                    lastY = e.clientY;

                    this.$el.on('mousemove', e2 => {
                        const threshold = options.editDragThreshold;

                        isDragging = isDragging || (
                            Math.abs(e2.clientX - lastX) > threshold ||
                            Math.abs(e2.clientY - lastY) > threshold);
                    });
                })
                .mouseup(() => {
                    this.$el.off('mousemove');

                    lastX = null;
                    lastY = null;
                });
        }
    }

    /**
     * Start editing.
     *
     * Args:
     *     options (EditOptions, optional):
     *         Options for the operation.
     */
    startEdit(options: EditOptions = {}) {
        if (this._editing || !this.options.enabled) {
            return;
        }

        let value;

        if (this.options.hasRawValue) {
            this._initialValue = this.options.rawValue;
            value = this._initialValue;
        } else {
            this._initialValue = this.$el.text();
            value = this.normalizeText(this._initialValue).htmlDecode();
        }

        this._editing = true;
        this.options.setFieldValue(this, value);

        this.trigger('beginEditPreShow', options);
        this.showEditor(options);
        this.trigger('beginEdit', options);
    }

    /**
     * Show the editor.
     *
     * Args:
     *     options (EditOptions, optional):
     *         Options for the operation.
     */
    showEditor(options: EditOptions = {}) {
        const $editIcon = this._$editIcon;

        if (this.options.multiline && !options.preventAnimation) {
            $editIcon.fadeOut(
                this.options.animationSpeedMS,
                () => $editIcon.css({
                    display: '',
                    visibility: 'hidden',
                }));
        } else {
            $editIcon.css('display', 'none');
        }

        this.$el.hide();
        this._$form.show();

        if (this.options.multiline) {
            const elHeight = this.$el.outerHeight();
            const newHeight = elHeight + this.options.extraHeight;

            if (this._isTextArea) {
                if (this.options.matchHeight) {
                    this.$field
                        .autoSizeTextArea('setMinHeight', newHeight)
                        .css('overflow', 'hidden');

                    if (options.preventAnimation) {
                        this.$field.height(newHeight);
                    } else {
                        this.$field
                            .height(elHeight)
                            .animate({ height: newHeight },
                                     this.options.animationSpeedMS);
                    }
                } else {
                    /*
                     * If there's significant processing that happens between
                     * the text and what's displayed in the element, it's
                     * likely that the rendered size will be different from the
                     * editor size. In that case, don't try to match sizes,
                     * just ask the field to auto-size itself to the size of
                     * the source text.
                     */
                    this.$field.autoSizeTextArea('autoSize', true, false,
                                                 elHeight);
                }
            }
        }

        this.$buttons.show();

        // Execute this after the animation, if we performed one.
        this.$field.queue(() => {
            if (this.options.multiline && this._isTextArea) {
                this.$field.css('overflow', 'auto');
            }

            if (this.options.focusOnOpen) {
                this.$field.focus();
            }

            if (!this.options.multiline &&
                this.$field[0].tagName === 'INPUT') {
                this.$field[0].select();
            }

            this.$field.dequeue();
        });
    }

    /**
     * Hide the inline editor.
     */
    hideEditor() {
        const $editIcon = this._$editIcon;

        this.$field.blur();
        this.$buttons.hide();

        if (this.options.multiline) {
            $editIcon.fadeIn(
                this.options.animationSpeedMS,
                () => $editIcon.css('visibility', 'visible'));
        } else {
            $editIcon.css('display', '');
        }

        if (this.options.multiline &&
            this.options.matchHeight &&
            this._editing &&
            this._isTextArea) {
            this.$field
                .css('overflow', 'hidden')
                .animate({ height: this.$el.outerHeight() },
                         this.options.animationSpeedMS);
        }

        this.$field.queue(() => {
            this.$el.show();
            this._$form.hide();
            this.$field.dequeue();
        });

        this._editing = false;
        this._updateDirtyState();
    }

    /**
     * Save the value of the editor.
     *
     * Args:
     *     options (SaveOptions):
     *         Options for the save operation.
     *
     * Returns:
     *     unknown:
     *     The new value, if available.
     */
    save(options: SaveOptions = {}): unknown {
        const value = this.getValue();
        const initialValue = this._initialValue;
        const dirty = this.isDirty();

        if (dirty) {
            this.$el.html(this.options.formatResult(value));
            this._initialValue = this.$el.text();
        }

        if (dirty || this.options.notifyUnchangedCompletion) {
            if (!options.preventEvents) {
                this.trigger('complete', value, initialValue);
            }

            if (this.options.hasRawValue) {
                this.options.rawValue = value;
            }

            return value;
        } else {
            if (!options.preventEvents) {
                this.trigger('cancel', this._initialValue);
            }
        }
    }

    /**
     * Submit the editor.
     *
     * Args:
     *     options (SaveOptions):
     *         Options for the save operation.
     *
     * Returns:
     *     unknown:
     *     The new value, if available.
     */
    submit(options: SaveOptions = {}) {
        // hideEditor() resets the _dirty flag, so we need to save() first.
        const value = this.save(options);
        this.hideEditor();

        return value;
    }

    /**
     * Cancel the edit.
     */
    cancel() {
        if (!this.isDirty() ||
            !this.options.promptOnCancel ||
            confirm(_`You have unsaved changes. Are you sure you want to discard them?`)) {
            this.hideEditor();
            this.trigger('cancel', this._initialValue);
        }
    }

    /**
     * Return the dirty state of the editor.
     *
     * Returns:
     *     boolean:
     *     Whether the editor is currently dirty.
     */
    isDirty(): boolean {
        if (this._dirtyCalcTimeout !== null) {
            clearTimeout(this._dirtyCalcTimeout);
            this._updateDirtyState();
        }

        return this._dirty;
    }

    /**
     * Return the value in the field.
     *
     * Returns:
     *     *:
     *     The current value of the field.
     */
    getValue(): unknown {
        return this.options.getFieldValue(this);
    }

    /**
     * Set the value in the field.
     *
     * Args:
     *     value (*):
     *     The new value for the field.
     */
    setValue(value: unknown) {
        this.options.setFieldValue(this, value);
        this._updateDirtyState();
    }

    /**
     * Enable the editor.
     */
    enable() {
        if (this._editing) {
            this.showEditor();
        }

        this._$editIcon.css('visibility', 'visible');
        this.options.enabled = true;
    }

    /**
     * Disable the editor.
     */
    disable() {
        if (this._editing) {
            this.hideEditor();
        }

        this._$editIcon.css('visibility', 'hidden');
        this.options.enabled = false;
    }

    /**
     * Return whether the editor is currently in edit mode.
     *
     * Returns:
     *     boolean:
     *     true if the inline editor is open.
     */
    editing(): boolean {
        return this._editing;
    }

    /**
     * Normalize the given text.
     *
     * Args:
     *     text (string):
     *         The text to normalize.
     *
     * Returns:
     *     string:
     *     The text with ``<br>`` elements turned into newlines and (in the
     *     case of multi-line data), whitespace collapsed.
     */
    normalizeText(text: string): string {
        if (this.options.stripTags) {
            /*
             * Turn <br> elements back into newlines before stripping out all
             * other tags. Without this, we lose multi-line data when editing
             * some legacy data.
             */
            text = text.replace(/<br>/g, '\n');
            text = text.stripTags().strip();
        }

        if (!this.options.multiline) {
            text = text.replace(/\s{2,}/g, ' ');
        }

        return text;
    }

    /**
     * Schedule an update for the dirty state.
     */
    _scheduleUpdateDirtyState() {
        if (this._dirtyCalcTimeout === null) {
            this._dirtyCalcTimeout = setTimeout(
                this._updateDirtyState.bind(this), 200);
        }
    }

    /**
     * Update the dirty state of the editor.
     */
    _updateDirtyState() {
        const newDirtyState = (
            this._editing &&
            this.options.isFieldDirty(this, this._initialValue));

        if (this._dirty !== newDirtyState) {
            this._dirty = newDirtyState;
            this.trigger('dirtyStateChanged', this._dirty);
        }

        this._dirtyCalcTimeout = null;
    }
}


interface RichTextInlineEditorViewOptions extends InlineEditorViewOptions {
    /** Options to pass through to the text editor. */
    textEditorOptions: Partial<TextEditorViewOptions>;
}


/**
 * A view for inline editors which use the CodeMirror editor for Markdown.
 */
@spina({
    prototypeAttrs: ['defaultOptions'],
})
export class RichTextInlineEditorView<
    TModel extends Backbone.Model = undefined,
    TElement extends HTMLElement = HTMLDivElement,
    TExtraViewOptions extends RichTextInlineEditorViewOptions =
        RichTextInlineEditorViewOptions
> extends InlineEditorView<TModel, TElement, TExtraViewOptions> {
    /**
     * Defaults for the view options.
     */
    static defaultOptions = _.defaults({
        getFieldValue: editor => editor.textEditor.getText(),
        isFieldDirty: (editor, initialValue) => {
            initialValue = editor.normalizeText(initialValue);

            return editor.textEditor.isDirty(initialValue);
        },
        matchHeight: false,
        multiline: true,
        setFieldValue: (editor, value) =>
            editor.textEditor.setText(value || ''),
    }, InlineEditorView.prototype.defaultOptions);

    /**********************
     * Instance variables *
     **********************/

    textEditor: TextEditorView;

    /**
     * Create and return the field to use for the input element.
     *
     * Returns:
     *     jQuery:
     *     The newly created input element.
     */
    createField(): JQuery {
        let origRichText;

        this.textEditor = new TextEditorView(
            this.options.textEditorOptions);
        this.textEditor.$el.on('resize', () => this.trigger('resize'));

        this.$el.data('text-editor', this.textEditor);

        this.once('beginEdit', () => {
            const $span = $('<span class="enable-markdown">');
            const $checkbox = $('<input type="checkbox">')
                .attr('id', _.uniqueId('markdown_check'))
                .change(() => _.defer(() => this._updateDirtyState()))
                .appendTo($span);

            this.textEditor.bindRichTextCheckbox($checkbox);

            $('<label>')
                .attr('for', $checkbox[0].id)
                .text(_`Enable Markdown`)
                .appendTo($span);

            this.$buttons.append($span);

            const $markdownRef = $('<a class="markdown-info" target="_blank">')
                .attr('href', `${MANUAL_URL}users/markdown/`)
                .text(_`Markdown Reference`)
                .toggle(this.textEditor.richText)
                .appendTo(this.$buttons);

            this.textEditor.bindRichTextVisibility($markdownRef);
        });

        this.listenTo(this, 'beginEdit', options => {
            if (options.clickX !== undefined && options.clickY !== undefined) {
                this.textEditor.setCursorPosition(options.clickX,
                                                  options.clickY);
            }

            this.textEditor.showEditor();

            origRichText = this.textEditor.richText;
        });

        this.listenTo(this, 'cancel', () => {
            this.textEditor.hideEditor();
            this.textEditor.setRichText(origRichText);
        });

        this.listenTo(this, 'complete', () => this.textEditor.hideEditor());

        return this.textEditor.render().$el;
    }

    /**
     * Set up events for the view.
     */
    setupEvents() {
        super.setupEvents();

        this.listenTo(this.textEditor, 'change',
                      this._scheduleUpdateDirtyState);
    }
}


interface DateInlineEditorViewOptions extends InlineEditorViewOptions {
    /** Optional text that can be prepended to the date picker. */
    descriptorText: string;

    /**
     * The optional earliest date that can be chosen in the date picker.
     *
     * This must be a local date in YYYY-MM-DD format.
     */
    minDate: string;

    /**
     * The optional latest date that can be chosen in the date picker.
     *
     * This must be a local date in YYYY-MM-DD format.
     */
    maxDate: string;
}


/**
 * A view for inline editors that edit dates.
 *
 * This view expects a local date in YYYY-MM-DD format to be passed to the
 * ``rawValue`` option and will render a date picker for editing the date.
 *
 * Version Added:
 *     5.0
 */
@spina({
    prototypeAttrs: ['defaultOptions'],
})
export class DateInlineEditorView<
    TModel extends Backbone.Model = undefined,
    TElement extends HTMLElement = HTMLDivElement,
    TExtraViewOptions extends DateInlineEditorViewOptions =
        DateInlineEditorViewOptions
> extends InlineEditorView<TModel, TElement, TExtraViewOptions> {
    /**
     * Defaults for the view options.
     */
    static defaultOptions = _.defaults({
        descriptorText: null,
        editIconClass: 'rb-icon rb-icon-edit',
        getFieldValue: editor => editor._$datePickerInput.val(),
        hasRawValue: true,
        isFieldDirty: (editor, initialValue) =>
            (editor.getValue() !== initialValue),
        maxDate: null,
        minDate: null,
        multiline: false,
        setFieldValue: (editor, value) =>
            editor._$datePickerInput.val(value),
        useEditIconOnly: true,
    }, InlineEditorView.prototype.defaultOptions);

    /**********************
     * Instance variables *
     **********************/

    _$datePicker: JQuery;
    _$datePickerInput: JQuery;

    /**
     * Create and return the date input element.
     *
     * Returns:
     *     jQuery:
     *     The newly created date input element.
     */
    createField(): JQuery {
        this._$datePickerInput = $('<input type="date"/>')
            .attr({
                'max': this.options.maxDate,
                'min': this.options.minDate,
            });

        this._$datePicker = $(
            '<span class="rb-c-date-inline-editor__picker">'
        )
        .append(this.options.descriptorText, this._$datePickerInput);

        return this._$datePicker;
    }

    /**
     * Connect events.
     */
    setupEvents() {
        super.setupEvents();

        this.$field.change(e => {
            e.stopPropagation();
            e.preventDefault();

            this._scheduleUpdateDirtyState();
        });
    }
}


/**
 * A view for inline editors that edit datetimes.
 *
 * This view expects a local datetime in YYYY-MM-DDThh:mm format to be
 * passed to the ``rawValue`` option and will render a datetime picker
 * for editing it.
 *
 * Version Added:
 *     5.0.2
 */
@spina
export class DateTimeInlineEditorView extends DateInlineEditorView {
    /**
     * Create and return the datetime input element.
     *
     * Returns:
     *     jQuery:
     *     The newly created datetime input element.
     */
    createField(): JQuery {
        this._$datePickerInput = $('<input type="datetime-local"/>')
            .attr({
                'max': this.options.maxDate,
                'min': this.options.minDate,
            });

        this._$datePicker = $(
            '<span class="rb-c-date-time-inline-editor__picker">'
        )
        .append(this.options.descriptorText, this._$datePickerInput);

        return this._$datePicker;
    }
}
