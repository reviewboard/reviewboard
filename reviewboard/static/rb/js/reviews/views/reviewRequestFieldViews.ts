/**
 * Views for review request fields.
 */

import { BaseView, spina } from '@beanbag/spina';

import {
    GetDraftFieldOptions,
    ReviewRequestEditor,
    SetDraftFieldOptions,
} from '../models/reviewRequestEditorModel';
import { ReviewRequestEditorView } from '../views/reviewRequestEditorView';


declare const SITE_ROOT: string;


/** Options for field views. */
interface BaseFieldViewOptions {
    /** The ID of the field. */
    fieldID: string;

    /**
     * The label for the field.
     *
     * Version Added:
     *     6.0
     */
    fieldLabel?: string;

    /** The name of the JSON field to use, if available. */
    jsonFieldName?: string;
}


/**
 * Base class for all field views.
 */
@spina({
    prototypeAttrs: [
        'editableProp',
        'useExtraData',
    ],
})
export class BaseFieldView extends BaseView<
    ReviewRequestEditor,
    HTMLDivElement,
    BaseFieldViewOptions
> {
    /**
     * The name of the property in the model for if this field is editable.
     */
    static editableProp = 'editable';

    /** Whether the contents of the field should be stored in extraData. */
    static useExtraData = true;

    /**********************
     * Instance variables *
     **********************/

    /** The ID of the field. */
    fieldID: string;

    /**
     * The label for the field.
     *
     * Version Added:
     *     6.0
     */
    fieldLabel: string;

    /** The name to use when storing the data as JSON. */
    jsonFieldName: string;

    /** The name of to use when storing the data in a model attribute. */
    _fieldName: string;

    /** The review request editor view. */
    reviewRequestEditorView: ReviewRequestEditorView;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (BaseFieldViewOptions):
     *         Options for the view.
     */
    initialize(options: BaseFieldViewOptions) {
        this.fieldID = options.fieldID;
        this.fieldLabel = options.fieldLabel || null;
        this.jsonFieldName = options.jsonFieldName ||
                             this.jsonFieldName ||
                             this.fieldID;
        this.$el.data('field-id', this.fieldID);
    }

    /**
     * The name of the attribute within the model.
     *
     * Returns:
     *     string:
     *     The name of the attribute that this field will reflect.
     */
    fieldName(): string {
        /*
         * This implementation will convert names with underscores to camel
         * case. This covers the typical naming between Python and JavaScript.
         * If subclasses need something different, they can override this with
         * either a new function or a regular attribute.
         */
        if (this._fieldName === undefined) {
            this._fieldName = this.fieldID.replace(
                /_(.)/g, (m, c) => c.toUpperCase());
        }

        return this._fieldName;
    }

    /**
     * Load the stored value for the field.
     *
     * This will load from the draft if representing a built-in field
     * (``useExtraData === false``) or from extra_data if a custom field
     * (``useExtraData === true``).
     *
     * Args:
     *     options (GetDraftFieldOptions):
     *         Options for :js:func:`RB.ReviewRequestEditor.getDraftField`.
     *
     * Returns:
     *     *:
     *     The stored value for the field.
     */
    _loadValue(
        options: GetDraftFieldOptions = {},
    ): unknown {
        const fieldName = (this.useExtraData
                           ? this.jsonFieldName
                           : _.result(this, 'fieldName'));

        return this.model.getDraftField(
            fieldName,
            _.defaults({
                useExtraData: this.useExtraData,
            }, options));
    }

    /**
     * Save a new value for the field.
     *
     * Args:
     *     value (*):
     *         The new value for the field.
     *
     *     options (SetDraftFieldOptions):
     *         Options for the save operation.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    _saveValue(
        value: unknown,
        options: SetDraftFieldOptions = {},
    ): Promise<void> {
        return this.model.setDraftField(
            _.result(this, 'fieldName'),
            value,
            _.defaults({
                jsonFieldName: this.jsonFieldName,
                useExtraData: this.useExtraData,
            }, options));
    }

    /**
     * Return whether the field has an unsaved editor open.
     *
     * This should be overridden by subclasses, if necessary.
     *
     * Returns:
     *     boolean:
     *     Whether the field is unsaved.
     */
    needsSave(): boolean {
        return false;
    }

    /**
     * Finish the field's save operation.
     *
     * This should be overridden by subclasses, if necessary.
     */
    finishSave() {
        // Intentionally left blank.
    }
}


/**
 * A field view for text-based fields.
 */
@spina({
    prototypeAttrs: [
        'autocomplete',
        'multiline',
        'useEditIconOnly',
    ],
})
export class TextFieldView extends BaseFieldView {
    /**
     * Autocomplete definitions.
     *
     * This should be overridden by subclasses.
     */
    static autocomplete = null;

    /** Whether the view is multi-line or single line. */
    static multiline = false;

    /**
     * Whether edits should be triggered only by clicking on the icon.
     *
     * If this is true, edits can only be triggered by clicking on the icon.
     * If this is false, clicks on the field itself will also trigger an edit.
     */
    static useEditIconOnly = false;

    /**********************
     * Instance variables *
     **********************/

    /** Whether the field allows Markdown-formatted text. */
    allowRichText = false;

    /** The inline editor view. */
    inlineEditorView: RB.InlineEditorView;

    /** The field name for storing the text type. */
    jsonTextTypeFieldName: string;

    /**
     * The model attribute for if this field is rich text.
     *
     * This is the name of the attribute which indicates whether the field
     * contains Markdown-formatted text or plain text.
     *
     * Returns:
     *     string:
     *     The name of the model atribute indicating whether the field contains
     *     rich text.
     */
    richTextAttr(): string {
        return this.allowRichText
               ? `${_.result(this, 'fieldName')}RichText`
               : null;
    }

    /**
     * Initialize the view.
     *
     * Args:
     *     options (BaseFieldViewOptions):
     *         Options for the view. See the parent class for details.
     */
    initialize(options: BaseFieldViewOptions) {
        super.initialize(options);

        this.jsonTextTypeFieldName = (this.jsonFieldName === 'text'
                                      ? 'text_type'
                                      : `${this.jsonFieldName}_text_type`);
    }

    /**
     * Return the type to use for the inline editor view.
     *
     * Returns:
     *     function:
     *     The constructor for the inline editor class to instantiate.
     */
    _getInlineEditorClass(): string {
        return (this.allowRichText
                ? RB.RichTextInlineEditorView
                : RB.InlineEditorView);
    }

    /**
     * Render the view.
     */
    onInitialRender() {
        if (!this.$el.hasClass('editable')) {
            return;
        }

        const fieldName = _.result(this, 'fieldName');
        const EditorClass = this._getInlineEditorClass();

        const inlineEditorOptions = {
            deferEventSetup: this.autocomplete !== null,
            editIconClass: 'rb-icon rb-icon-edit',
            el: this.$el,
            enabled: this.model.get(this.editableProp),
            fieldLabel: this.fieldLabel,
            formClass: `${this.$el.prop('id')}-editor`,
            hasShortButtons: !this.multiline,
            multiline: this.multiline,
            showRequiredFlag: this.$el.hasClass('required'),
            useEditIconOnly: this.useEditIconOnly,
        };

        if (this.allowRichText) {
            _.extend(inlineEditorOptions, {
                fieldName: this.fieldName,
                hasRawValue: true,
                matchHeight: false,
                rawValue: this._loadValue({
                    useRawTextValue: true,
                }) || '',
                textEditorOptions: {
                    minHeight: 0,
                    richText: this._loadRichTextValue(),
                },
            });
        }

        this.inlineEditorView = new EditorClass(inlineEditorOptions);
        this.inlineEditorView.render();

        this.listenTo(this.inlineEditorView, 'beginEdit',
                      () => this.model.incr('editCount'));

        this.listenTo(this.inlineEditorView, 'resize',
                      () => this.trigger('resize'));

        this.listenTo(this.inlineEditorView, 'cancel', () => {
            this.trigger('resize');
            this.model.decr('editCount');
        });

        this.listenTo(this.inlineEditorView, 'complete', value => {
            this.trigger('resize');
            this.model.decr('editCount');

            const saveOptions = {
                allowMarkdown: this.allowRichText,
            };

            if (this.allowRichText) {
                saveOptions.richText =
                    this.inlineEditorView.textEditor.richText;
                saveOptions.jsonTextTypeFieldName = this.jsonTextTypeFieldName;
            }

            this._saveValue(value, saveOptions)
                .then(() => {
                    this._formatField();
                    this.trigger('fieldSaved');
                })
                .catch(err => {
                    this._formatField();
                    this.trigger('fieldError', err.message);
                });
        });

        if (this.autocomplete !== null) {
            this._buildAutoComplete();
            this.inlineEditorView.setupEvents();
        }

        this.listenTo(
            this.model,
            `change:${this.editableProp}`,
            (model, editable) => {
                if (editable) {
                    this.inlineEditorView.enable();
                } else {
                    this.inlineEditorView.disable();
                }
            });

        this.listenTo(this.model, `fieldChanged:${fieldName}`,
                      this._formatField);
    }

    /**
     * Convert an item to a hyperlink.
     *
     * Args:
     *     item (object):
     *         The item to link. The content is up to the caller.
     *
     *     options (object):
     *         Options to control the linking behavior.
     *
     * Option Args:
     *     cssClass (string, optional):
     *         The optional CSS class to add to the link.
     *
     *     makeItemText (function, optional):
     *         A function that takes the item and returns the text for the
     *         link. If not specified, the item itself will be used as the
     *         text.
     *
     *     makeItemURL (function, optional):
     *         A function that takes the item and returns the URL for the link.
     *         If not specified, the item itself will be used as the URL.
     *
     * Returns:
     *     jQuery:
     *     The resulting link element wrapped in jQuery.
     */
    _convertToLink(
        item: unknown,
        options: {
            cssClass?: string;
            makeItemText?: (unknown) => string;
            makeItemURL?: (unknown) => string;
        } = {},
    ): JQuery {
        if (!item) {
            return $();
        }

        const $link = $('<a/>')
            .attr('href', (options.makeItemURL
                           ? options.makeItemURL(item)
                           : item))
            .text(options.makeItemText ? options.makeItemText(item) : item);

        if (options.cssClass) {
            $link.addClass(options.cssClass);
        }

        return $link;
    }

    /**
     * Add auto-complete functionality to the field.
     */
    _buildAutoComplete() {
        const ac = this.autocomplete;
        const reviewRequest = this.model.get('reviewRequest');

        this.inlineEditorView.$field
            .rbautocomplete({
                cmp: ac.cmp,
                error: xhr => {
                    let text;

                    try {
                        text = JSON.parse(xhr.responseText).err.msg;
                    } catch (e) {
                        text = `HTTP ${xhr.status} ${xhr.statusText}`;
                    }

                    alert(text);
                },
                extraParams: ac.extraParams,
                formatItem: data => {
                    let s = data[ac.nameKey];

                    if (ac.descKey && data[ac.descKey]) {
                        s += ` <span>(${_.escape(data[ac.descKey])})</span>`;
                    }

                    return s;
                },
                matchCase: false,
                multiple: true,
                parse: data => {
                    const items = _.isFunction(ac.fieldName)
                                  ? ac.fieldName(data)
                                  : data[ac.fieldName];

                    return items.map(item => {
                        if (ac.parseItem) {
                            item = ac.parseItem(item);
                        }

                        return {
                            data: item,
                            result: item[ac.nameKey],
                            value: item[ac.nameKey],
                        };
                    });
                },
                url: SITE_ROOT + reviewRequest.get('localSitePrefix') +
                     'api/' + (ac.resourceName || ac.fieldName) + '/',
                width: 350,
            })
            .on('autocompleteshow', () => {
                /*
                 * Add the footer to the bottom of the results pane the
                 * first time it's created.
                 *
                 * Note that we may have multiple .ui-autocomplete-results
                 * elements, and we don't necessarily know which is tied to
                 * this. So, we'll look for all instances that don't contain
                 * a footer.
                 */
                const resultsPane = $('.ui-autocomplete-results:not(' +
                                      ':has(.ui-autocomplete-footer))');

                if (resultsPane.length > 0) {
                    $('<div/>')
                        .addClass('ui-autocomplete-footer')
                        .text(gettext('Press Tab to auto-complete.'))
                        .appendTo(resultsPane);
                }
            });
    }

    /**
     * Format the contents of the field.
     *
     * This will apply the contents of the model attribute to the field
     * element. If the field defines a ``formatValue`` method, this will use
     * that to do the formatting. Otherwise, the element will just be set to
     * contain the text of the value.
     */
    _formatField() {
        const value = this._loadValue();

        if (_.isFunction(this.formatValue)) {
            this.formatValue(value);
        } else {
            this.$el.text(value);
        }
    }

    /**
     * Return whether the field has an unsaved editor open.
     *
     * Returns:
     *     boolean:
     *     Whether the field is unsaved.
     */
    needsSave(): boolean {
        return this.inlineEditorView && this.inlineEditorView.isDirty();
    }

    /**
     * Finish the field's save operation.
     */
    finishSave(): Promise<void> {
        const value = this.inlineEditorView.submit({
            preventEvents: true,
        });

        if (value) {
            this.trigger('resize');
            this.model.decr('editCount');

            const saveOptions = {
                allowMarkdown: this.allowRichText,
            };

            if (this.allowRichText) {
                saveOptions.richText =
                    this.inlineEditorView.textEditor.richText;
                saveOptions.jsonTextTypeFieldName = this.jsonTextTypeFieldName;
            }

            return this._saveValue(value, saveOptions)
                .then(() => {
                    this._formatField();
                    this.trigger('fieldSaved');
                })
                .catch(err => {
                    this._formatField();
                    this.trigger('fieldError', err.message);
                });
        } else {
            return Promise.resolve();
        }
    }

    /**
     * Load the rich text value for the field.
     *
     * This will look up the rich text boolean attribute for built-in
     * fields or the text type information in extra_data, returning
     * whether the field is set to use rich text.
     *
     * Returns:
     *     boolean:
     *     Whether the field is set for rich text. This will be
     *     ``undefined`` if an explicit value isn't stored.
     */
    _loadRichTextValue(): boolean {
        if (this.useExtraData) {
            const textTypeFieldName = this.jsonTextTypeFieldName;
            const textType = this.model.getDraftField(
                textTypeFieldName,
                {
                    useExtraData: true,
                    useRawTextValue: true,
                });

            if (textType === undefined) {
                return undefined;
            }

            console.assert(
                textType === 'plain' || textType === 'markdown',
                `Text type "${textType}" in field "${textTypeFieldName}" ` +
                `not supported.`);

            return textType === 'markdown';
        } else {
            return this.model.getDraftField(_.result(this, 'richTextAttr'));
        }
    }
}


/**
 * A field view for multiline text-based fields.
 */
@spina({
    prototypeAttrs: [
        'multiline',
    ],
})
export class MultilineTextFieldView extends TextFieldView {
    static multiline = true;

    allowRichText = null;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (BaseFieldViewOptions):
     *         Options for the view.
     */
    initialize(options: BaseFieldViewOptions) {
        super.initialize(options);

        /*
         * If this field is coming from an extension which doesn't specify any
         * JS-side version, we need to pull some data out of the markup.
         */
        if (this.allowRichText === null) {
            this.allowRichText = this.$el.data('allow-markdown');

            const reviewRequest = this.model.get('reviewRequest');
            const extraData = reviewRequest.draft.get('extraData');

            const rawValue = this.$el.data('raw-value');
            extraData[this.jsonFieldName] = (rawValue !== undefined
                                             ? rawValue || ''
                                             : this.$el.text());
            this.$el.removeAttr('data-raw-value');

            if (this.allowRichText) {
                extraData[this.jsonTextTypeFieldName] =
                    (this.$el.hasClass('rich-text') ? 'markdown' : 'plain');
            }
        }
    }

    /**
     * Linkify a block of text.
     *
     * This turns URLs, /r/#/ paths, and bug numbers into clickable links. It's
     * a wrapper around RB.formatText that handles passing in the bug tracker.
     *
     * Args:
     *     options (object):
     *         Options for the text formatting.
     *
     * Option Args:
     *     newText (string, optional):
     *         The new text to format into the element. If not specified, the
     *         existing contents of the element are used.
     */
    formatText(
        options: {
            newText?: string;
        } = {},
    ) {
        const reviewRequest = this.model.get('reviewRequest');

        options = _.defaults({
            bugTrackerURL: reviewRequest.get('bugTrackerURL'),
            isHTMLEncoded: true,
        }, options);

        if (this.allowRichText) {
            options.richText = this._loadRichTextValue();
        }

        RB.formatText(this.$el, options);

        this.$('img').on('load', () => this.trigger('resize'));
    }

    /**
     * Render the view.
     */
    onInitialRender() {
        super.onInitialRender();
        this.formatText();
    }

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (object):
     *         The new value of the field.
     */
    formatValue(data: string) {
        if (this.allowRichText) {
            this.formatText({ newText: data });
        }
    }
}


/**
 * A field view for fields that include multiple comma-separated values.
 */
@spina({
    prototypeAttrs: ['useEditIconOnly'],
})
export class CommaSeparatedValuesTextFieldView extends TextFieldView {
    static useEditIconOnly = true;

    /**
     * Convert an array of items to a list of hyperlinks.
     *
     * Args:
     *     list (Array);
     *         An array of items. The contents of the item is up to the caller.
     *
     *     options (object):
     *         Options to control the linking behavior.
     *
     * Option Args:
     *     cssClass (string, optional):
     *         The optional CSS class to add for each link.
     *
     *     makeItemText (function, optional):
     *         A function that takes an item and returns the text for the link.
     *         If not specified, the item itself will be used as the text.
     *
     *     makeItemURL (function, optional):
     *         A function that takes an item and returns the URL for the link.
     *         If not specified, the item itself will be used as the URL.
     *
     * Returns:
     *     jQuery:
     *     The resulting link elements in a jQuery list.
     */
    _urlizeList(
        list: unknown[],
        options: {
            cssClass?: string;
            makeItemText?: (unknown) => string;
            makeItemURL?: (unknown) => string;
        } = {},
    ): JQuery {
        let $links = $();

        if (list) {
            for (let i = 0; i < list.length; i++) {
                $links = $links.add(this._convertToLink(list[i], options));

                if (i < list.length - 1) {
                    $links = $links.add(document.createTextNode(', '));
                }
            }
        }

        return $links;
    }

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (Array):
     *         The new value of the field.
     */
    formatValue(data?: string[]) {
        data = data || [];
        this.$el.html(data.join(', '));
    }
}


/**
 * A field view for checkbox fields.
 */
@spina
export class CheckboxFieldView extends BaseFieldView {
    /**
     * Render the field.
     */
    onInitialRender() {
        this.$el.change(() => {
            this._saveValue(this.$el.is(':checked'))
                .then(() => this.trigger('fieldSaved'))
                .catch(err => this.trigger('fieldError', err.message));
        });
    }
}


/**
 * A field view for dropdown fields.
 */
@spina
export class DropdownFieldView extends BaseFieldView {
    /**
     * Render the field.
     */
    onInitialRender() {
        super.onInitialRender();

        this.$el.change(() => {
            this._saveValue(this.$el.val())
                .then(() => this.trigger('fieldSaved'))
                .catch(err => this.trigger('fieldError', err.message));
        });
    }
}


/**
 * A field view for date fields.
 */
@spina
export class DateFieldView extends TextFieldView {
    /**
     * Render the field.
     */
    onInitialRender() {
        super.onInitialRender();

        this.inlineEditorView.$field
            .datepicker({
                changeMonth: true,
                changeYear: true,
                dateFormat: $.datepicker.ISO_8601,
                onSelect: (dateText, instance) => {
                    if (dateText !== instance.lastVal) {
                        this.inlineEditorView._dirty = true;
                    }
                },
                showButtonPanel: true,
            });
    }

    /**
     * Save a new value for the field.
     *
     * Args:
     *     value (*):
     *         The new value for the field.
     *
     *     options (object):
     *         Options for the save operation.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    _saveValue(
        value: unknown,
        options: SetDraftFieldOptions = {},
    ): Promise<void> {
        const m = moment(value, 'YYYY-MM-DD', true);

        if (!m.isValid()) {
            value = '';
            this.$el.text('');
        }

        return super._saveValue(value, options);
    }
}


/**
 * The "Branch" field.
 */
@spina({
    prototypeAttrs: ['useExtraData'],
})
export class BranchFieldView extends TextFieldView {
    static useExtraData = false;
}


/**
 * The "Bugs" field.
 */
@spina({
    prototypeAttrs: ['useExtraData'],
})
export class BugsFieldView extends CommaSeparatedValuesTextFieldView {
    static useExtraData = false;

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (Array):
     *         The new value of the field.
     */
    formatValue(data: string[]) {
        data = data || [];

        const reviewRequest = this.model.get('reviewRequest');
        const bugTrackerURL = reviewRequest.get('bugTrackerURL');

        if (bugTrackerURL) {
            this.$el
                .empty()
                .append(this._urlizeList(data, {
                    cssClass: 'bug',
                    makeItemURL: item => bugTrackerURL.replace(
                        '--bug_id--', item),
                }))
                .find('.bug').bug_infobox();
        } else {
            this.$el.text(data.join(', '));
        }
    }
}


/**
 * The change description field.
 */
@spina({
    prototypeAttrs: ['useExtraData'],
})
export class ChangeDescriptionFieldView extends MultilineTextFieldView {
    static useExtraData = false;

    /**********************
     * Instance variables *
     **********************/

    allowRichText = true;
    jsonFieldName = 'changedescription';
}


/**
 * The commit list field.
 *
 * This provides expand/collapse functionality for commit messages that are
 * more than a single line.
 */
@spina
export class CommitListFieldView extends BaseFieldView {
    /**********************
     * Instance variables *
     **********************/

    #commitListView: RB.DiffCommitListView = null;

    /**
     * Render the field.
     */
    onInitialRender() {
        super.onInitialRender();

        /*
         * We needn't render the view because it has already been rendered by
         * the server.
         */
        this.#commitListView = new RB.DiffCommitListView({
            el: this.$('.commit-list'),
            model: new RB.DiffCommitList({
                commits: this.model.get('commits'),
                isInterdiff: false,
            }),
        });
    }
}


/**
 * The close description field.
 */
@spina({
    prototypeAttrs: [
        'editableProp',
        'useExtraData',
    ],
})
export class CloseDescriptionFieldView extends MultilineTextFieldView {
    static editableProp = 'statusEditable';
    static useExtraData = false;

    /**********************
     * Instance variables *
     **********************/

    allowRichText = true;
    closeType: string;

    /**
     * Save a new value for the field.
     *
     * Args:
     *     value (*):
     *         The new value for the field.
     *
     *     options (object):
     *         Options for the save operation.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    _saveValue(
        value: string,
        options: SetDraftFieldOptions = {},
    ): Promise<void> {
        return this.model.get('reviewRequest').close(_.defaults({
            description: value,
            postData: {
                force_text_type: 'html',
                include_text_types: 'raw',
            },
            type: this.closeType,
        }, options));
    }
}


/**
 * The "Depends On" field.
 */
@spina({
    prototypeAttrs: [
        'autocomplete',
        'useEditIconOnly',
        'useExtraData',
    ],
})
export class DependsOnFieldView extends CommaSeparatedValuesTextFieldView {
    static autocomplete = {
        cmp: (term, a, b) => b.data.id - a.data.id,
        descKey: 'id',
        display_name: 'summary',
        extraParams: {
            summary: 1,
        },
        fieldName: data => data.search.review_requests,
        nameKey: 'id',
        parseItem: item => {
            item.id = item.id.toString();
            item.display_name = item.summary;

            return item;
        },
        resourceName: 'search',
    };

    static useEditIconOnly = true;
    static useExtraData = false;

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (Array):
     *         The new value of the field.
     */
    formatValue(data: string[]) {
        data = data || [];

        this.$el
            .empty()
            .append(this._urlizeList(data, {
                cssClass: 'review-request-link',
                makeItemText: item => item.id,
                makeItemURL: item => item.url,
            }))
            .find('.review-request-link').review_request_infobox();
    }
}


/**
 * The "Description" field.
 */
@spina({
    prototypeAttrs: ['useExtraData'],
})
export class DescriptionFieldView extends MultilineTextFieldView {
    static useExtraData = false;

    allowRichText = true;
}


/**
 * The "Owner" field.
 */
@spina({
    prototypeAttrs: [
        'autocomplete',
        'useEditIconOnly',
        'useExtraData',
    ],
})
export class OwnerFieldView extends TextFieldView {
    static autocomplete = {
        cmp: (term, a, b) => {
            /*
             * Sort the results with username matches first (in alphabetical
             * order), followed by real name matches (in alphabetical order).
             */
            const aUsername = a.data.username;
            const bUsername = b.data.username;
            const aFullname = a.data.fullname;
            const bFullname = a.data.fullname;

            if (aUsername.indexOf(term) === 0) {
                if (bUsername.indexOf(term) === 0) {
                    return aUsername.localeCompare(bUsername);
                }

                return -1;
            } else if (bUsername.indexOf(term) === 0) {
                return 1;
            } else {
                return aFullname.localeCompare(bFullname);
            }
        },
        descKey: 'fullname',
        extraParams: {
            fullname: 1,
        },
        fieldName: 'users',
        nameKey: 'username',
    };

    static useEditIconOnly = true;
    static useExtraData = false;

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (string):
     *         The new value of the field.
     */
    formatValue(data: string) {
        const $link = this._convertToLink(
            data,
            {
                cssClass: 'user',
                makeItemText: item => item.title,
                makeItemURL: item => {
                    const href = item.href;

                    return href.substr(href.indexOf('/users'));
                },
            });

        this.$el
            .empty()
            .append($link.user_infobox());
    }
}


/**
 * The "Summary" field.
 */
@spina({
    prototypeAttrs: ['useExtraData'],
})
export class SummaryFieldView extends TextFieldView {
    static useExtraData = false;
}


/**
 * The "Groups" field.
 */
@spina({
    prototypeAttrs: [
        'autocomplete',
        'useEditIconOnly',
        'useExtraData',
    ],
})
export class TargetGroupsFieldView extends CommaSeparatedValuesTextFieldView {
    static autocomplete = {
        descKey: 'display_name',
        extraParams: {
            displayname: 1,
        },
        fieldName: 'groups',
        nameKey: 'name',
    };

    static useEditIconOnly = true;
    static useExtraData = false;

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (Array):
     *         The new value of the field.
     */
    formatValue(data: string[]) {
        data = data || [];

        this.$el
            .empty()
            .append(this._urlizeList(data, {
                makeItemText: item => item.name,
                makeItemURL: item => item.url,
            }));
    }
}


/**
 * The "People" field.
 */
@spina({
    prototypeAttrs: [
        'autocomplete',
        'useEditIconOnly',
        'useExtraData',
    ],
})
export class TargetPeopleFieldView extends CommaSeparatedValuesTextFieldView {
    static autocomplete = {
        cmp: (term, a, b) => {
            /*
             * Sort the results with username matches first (in alphabetical
             * order), followed by real name matches (in alphabetical order).
             */
            const aUsername = a.data.username;
            const bUsername = b.data.username;
            const aFullname = a.data.fullname;
            const bFullname = a.data.fullname;

            if (aUsername.indexOf(term) === 0) {
                if (bUsername.indexOf(term) === 0) {
                    return aUsername.localeCompare(bUsername);
                }

                return -1;
            } else if (bUsername.indexOf(term) === 0) {
                return 1;
            } else {
                return aFullname.localeCompare(bFullname);
            }
        },
        descKey: 'fullname',
        extraParams: {
            fullname: 1,
        },
        fieldName: 'users',
        nameKey: 'username',
    };

    static useEditIconOnly = true;
    static useExtraData = false;

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (Array):
     *         The new value of the field.
     */
    formatValue(data: string[]) {
        data = data || [];
        this.$el
            .empty()
            .append(this._urlizeList(data, {
                cssClass: 'user',
                makeItemText: item => item.username,
                makeItemURL: item => item.url,
            }))
            .find('.user').user_infobox();
    }
}


/**
 * The "Testing Done" field.
 */
@spina({
    prototypeAttrs: ['useExtraData'],
})
export class TestingDoneFieldView extends MultilineTextFieldView {
    static useExtraData = false;

    allowRichText = true;
}
