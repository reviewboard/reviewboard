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
        editIconClass: null,
        editIconPath: null,
        enabled: true,
        extraHeight: 100,
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
    $field: JQuery;
    options: TExtraViewOptions;
    _$editIcon: JQuery;
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
        this.$el.data('inline-editor', this);

        this._$form = $('<form>')
            .addClass(`inline-editor-form ${this.options.formClass}`)
            .css('display', 'inline')
            .hide()
            .insertBefore(this.$el);

        this.$field = this.createField()
            .prependTo(this._$form);
        this._isTextArea = (this.$field[0].tagName === 'TEXTAREA');

        this.$buttons = $();

        if (this.options.showButtons) {
            this.$buttons = $(this.options.multiline ? '<div>' : '<span>')
                .hide()
                .addClass('buttons')
                .appendTo(this._$form);

            $('<input type="button" class="save">')
                .val(_`OK`)
                .appendTo(this.$buttons)
                .click(this.submit.bind(this));

            $('<input type="button" class="cancel">')
                .val(_`Cancel`)
                .appendTo(this.$buttons)
                .click(this.cancel.bind(this));
        }

        this._$editIcon = $();

        if (this.options.showEditIcon) {
            const editText = _`Edit this field`;
            this._$editIcon = $('<a class="editicon" href="#" role="button">')
                .attr({
                    'aria-label': editText,
                    'title': editText,
                })
                .click(e => {
                    e.preventDefault();
                    e.stopPropagation();

                    this.startEdit();
                });

            if (this.options.editIconPath) {
                this._$editIcon.append(
                    `<img src="${this.options.editIconPath}">`);
            } else if (this.options.editIconClass) {
                this._$editIcon.append(
                    `<div class="${this.options.editIconClass}" aria-hidden="true"></div>`);
            }

            if (this.options.showRequiredFlag) {
                const requiredText = _`This field is required`;
                $('<span class="required-flag">*</span>')
                    .attr({
                        'aria-label': requiredText,
                        'title': requiredText,
                    })
                    .appendTo(this._$editIcon);
            }

            if (this.options.multiline && this.$el[0].id) {
                $(`label[for="${this.$el[0].id}"]`)
                    .append(this._$editIcon);
            } else {
                this._$editIcon.insertAfter(this.$el);
            }
        }

        if (!this.options.deferEventSetup) {
            this.setupEvents();
        }

        if (this.options.startOpen) {
            this.startEdit({
                preventAnimation: true,
            });
        }

        if (this.options.enabled) {
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
        this.$field
            .keydown(e => {
                e.stopPropagation();

                if (e.key === 'Enter') {
                    if (!this.options.multiline || e.ctrlKey) {
                        this.submit();
                    }

                    if (!this.options.multiline) {
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
            .on('cut paste', () => this._scheduleUpdateDirtyState())

        if (!this.options.useEditIconOnly) {
            /*
             * Check if the mouse was dragging, so that the editor isn't opened
             * when text is selected.
             */
            let isDragging = true;

            this.$el
                .on('click', 'a', e => e.stopPropagation())
                .click(e => {
                    e.stopPropagation();
                    e.preventDefault();

                    if (!isDragging) {
                        this.startEdit();
                    }

                    isDragging = true;
                })
                .mousedown(() => {
                    isDragging = false;
                    this.$el.one('mousemove', () => {
                        isDragging = true;
                    });
                })
                .mouseup(() => {
                    this.$el.unbind('mousemove');
                });
        }

        $(window).on(`resize.${this.cid}`, this._fitWidthToParent());
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

        this.trigger('beginEditPreShow');
        this.showEditor(options);
        this.trigger('beginEdit');
    }

    /**
     * Show the editor.
     *
     * Args:
     *     options (EditOptions, optional):
     *         Options for the operation.
     */
    showEditor(options: EditOptions = {}) {
        if (this.options.multiline && !options.preventAnimation) {
            this._$editIcon.fadeOut(this.options.animationSpeedMS);
        } else {
            this._$editIcon.hide();
        }

        this.$el.hide();
        this._$form.show();

        if (this.options.multiline) {
            const elHeight = this.$el.outerHeight();
            const newHeight = elHeight + this.options.extraHeight;

            this._fitWidthToParent();

            if (this._isTextArea) {
                if (this.options.matchHeight) {
                    // TODO: Set autosize min height
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

            this._fitWidthToParent();

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
        this.$field.blur();
        this.$buttons.hide();

        if (this.options.multiline) {
            this._$editIcon.fadeIn(this.options.animationSpeedMS);
        } else {
            this._$editIcon.show();
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

        this._$editIcon.show();
        this.options.enabled = true;
    }

    /**
     * Disable the editor.
     */
    disable() {
        if (this._editing) {
            this.hideEditor();
        }

        this._$editIcon.hide();
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

    /**
     * Fit the editor width to the parent element.
     */
    _fitWidthToParent() {
        if (!this._editing) {
            return;
        }

        if (this.options.multiline) {
            this.$field.css({
                'box-sizing': 'border-box',
                'width': '100%',
            });

            return;
        }

        const $formParent = this._$form.parent();
        const parentTextAlign = $formParent.css('text-align');
        const isLeftAligned = (parentTextAlign === 'left');

        if (!isLeftAligned) {
            $formParent.css('text-align', 'left');
        }

        const boxSizing = this.$field.css('box-sizing');
        let extentTypes;

        if (boxSizing === 'border-box') {
            extentTypes = 'm';
        } else if (boxSizing === 'padding-box') {
            extentTypes = 'p';
        } else {
            extentTypes = 'bmp';
        }

        let buttonsWidth = 0;

        if (this.$buttons.length !== 0) {
            const buttonsDisplay = this.$buttons.css('display');

            if (buttonsDisplay === 'inline' ||
                buttonsDisplay === 'inline-block') {
                /*
                 * The buttons are set for the same line as the field, so
                 * factor the width of the buttons container into the field
                 * width calculation below.
                 */
                buttonsWidth = this.$buttons.outerWidth();
            }
        }

        /*
         * First make the field really small so it will fit without wrapping,
         * then figure out the offset and use it to calculate the desired
         * width.
         */
        this.$field
            .width(0)
            .outerWidth(
                $formParent.innerWidth() -
                (this._$form.offset().left - $formParent.offset().left) -
                this.$field.getExtents(extentTypes, 'lr') -
                buttonsWidth);

        if (!isLeftAligned) {
            $formParent.css('text-align', parentTextAlign);
        }
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

        this.listenTo(this, 'beginEdit', () => {
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
