(function() {


const Fields = {};


/**
 * Base class for all field views.
 */
Fields.BaseFieldView = Backbone.View.extend({
    /**
     * The name of the property in the model for if this field is editable.
     */
    editableProp: 'editable',

    /** Whether the contents of the field should be stored in extraData. */
    useExtraData: true,

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     fieldID (string):
     *         The ID of the field.
     */
    initialize(options) {
        this.fieldID = options.fieldID;
        this.jsonFieldName = options.jsonFieldName ||
                             this.jsonFieldName ||
                             this.fieldID;
        this._fieldName = undefined;
        this.$el.data('field-id', this.fieldID);
    },

    /**
     * The name of the attribute within the model.
     *
     * Returns:
     *     string:
     *     The namee of the attribute that this field will reflect.
     */
    fieldName() {
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
    },

    /**
     * Load the stored value for the field.
     *
     * This will load from the draft if representing a built-in field
     * (``useExtraData === false``) or from extra_data if a custom field
     * (``useExtraData === true``).
     *
     * Args:
     *     options (object):
     *         Options for :js:func:`RB.ReviewRequestEditor.getDraftField`.
     *
     * Returns:
     *     *:
     *     The stored value for the field.
     */
    _loadValue(options) {
        const fieldName = (this.useExtraData
                           ? this.jsonFieldName
                           : _.result(this, 'fieldName'));

        return this.model.getDraftField(
            fieldName,
            _.defaults({
                useExtraData: this.useExtraData,
            }, options));
    },

    /**
     * Save a new value for the field.
     *
     * Args:
     *     value (*):
     *         The new value for the field.
     *
     *     options (object):
     *         Options for the save operation.
     */
    _saveValue(value, options) {
        this.model.setDraftField(
            _.result(this, 'fieldName'),
            value,
            _.defaults({
                jsonFieldName: this.jsonFieldName,
                useExtraData: this.useExtraData,
            }, options));
    },

    /**
     * Return whether the field has an unsaved editor open.
     *
     * This should be overridden by subclasses, if necessary.
     *
     * Returns:
     *     boolean:
     *     Whether the field is unsaved.
     */
    needsSave() {
        return false;
    },

    /**
     * Finish the field's save operation.
     *
     * This should be overridden by subclasses, if necessary.
     */
    finishSave() {
    },
});


/**
 * A field view for text-based fields.
 */
Fields.TextFieldView = Fields.BaseFieldView.extend({
    /**
     * Autocomplete definitions.
     *
     * This should be overridden by subclasses.
     */
    autocomplete: null,

    /** Whether the view is multi-line or single line. */
    multiline: false,

    /** Whether the field allows Markdown-formatted text. */
    allowRichText: false,

    /**
     * Whether edits should be triggered only by clicking on the icon.
     *
     * If this is true, edits can only be triggered by clicking on the icon.
     * If this is false, clicks on the field itself will also trigger an edit.
     */
    useEditIconOnly: false,

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
    richTextAttr() {
        return this.allowRichText
               ? `${_.result(this, 'fieldName')}RichText`
               : null;
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view. See the parent class for details.
     */
    initialize(options) {
        Fields.BaseFieldView.prototype.initialize.call(this, options);

        this.jsonTextTypeFieldName = (this.jsonFieldName === 'text'
                                      ? 'text_type'
                                      : `${this.jsonFieldName}_text_type`);
    },

    /**
     * Return the type to use for the inline editor view.
     *
     * Returns:
     *     function:
     *     The constructor for the inline editor class to instantiate.
     */
    _getInlineEditorClass() {
        return (this.allowRichText
                ? RB.RichTextInlineEditorView
                : RB.InlineEditorView);
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.ReviewRequestFields.TextFieldView:
     *     This object, for chaining.
     */
    render() {
        if (!this.$el.hasClass('editable')) {
            return this;
        }

        const fieldName = _.result(this, 'fieldName');
        const EditorClass = this._getInlineEditorClass();

        const inlineEditorOptions = {
            el: this.$el,
            formClass: `${this.$el.prop('id')}-editor`,
            editIconClass: 'rb-icon rb-icon-edit',
            enabled: this.model.get(this.editableProp),
            multiline: this.multiline,
            useEditIconOnly: this.useEditIconOnly,
            showRequiredFlag: this.$el.hasClass('required'),
            deferEventSetup: this.autocomplete !== null,
        };

        if (this.allowRichText) {
            _.extend(inlineEditorOptions, {
                textEditorOptions: {
                    minHeight: 0,
                    richText: this._loadRichTextValue(),
                },
                matchHeight: false,
                hasRawValue: true,
                rawValue: this._loadValue({
                    useRawTextValue: true,
                }) || '',
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
                error: err => {
                    this._formatField();
                    this.trigger('fieldError', err);
                },
                success: () => {
                    this._formatField();
                    this.trigger('fieldSaved');
                },
            };

            if (this.allowRichText) {
                saveOptions.richText =
                    this.inlineEditorView.textEditor.richText;
                saveOptions.jsonTextTypeFieldName = this.jsonTextTypeFieldName;
            }

            this._saveValue(value, saveOptions);
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

        return this;
    },

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
    _convertToLink(item, options={}) {
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
    },

    /**
     * Add auto-complete functionality to the field.
     */
    _buildAutoComplete() {
        const ac = this.autocomplete;
        const reviewRequest = this.model.get('reviewRequest');

        this.inlineEditorView.$field
            .rbautocomplete({
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
                            value: item[ac.nameKey],
                            result: item[ac.nameKey],
                        };
                    });
                },
                url: SITE_ROOT + reviewRequest.get('localSitePrefix') +
                     'api/' + (ac.resourceName || ac.fieldName) + '/',
                extraParams: ac.extraParams,
                cmp: ac.cmp,
                width: 350,
                error: xhr => {
                    let text;

                    try {
                        text = JSON.parse(xhr.responseText).err.msg;
                    } catch (e) {
                        text = `HTTP ${xhr.status} ${xhr.statusText}`;
                    }

                    alert(text);
                },
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
    },

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
    },

    /**
     * Return whether the field has an unsaved editor open.
     *
     * Returns:
     *     boolean:
     *     Whether the field is unsaved.
     */
    needsSave() {
        return this.inlineEditorView && this.inlineEditorView.isDirty();
    },

    /**
     * Finish the field's save operation.
     */
    finishSave() {
        this.inlineEditorView.submit();
    },

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
    _loadRichTextValue() {
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
    },
});


/**
 * A field view for multiline text-based fields.
 */
Fields.MultilineTextFieldView = Fields.TextFieldView.extend({
    multiline: true,
    allowRichText: null,

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     */
    initialize(options) {
        Fields.TextFieldView.prototype.initialize.call(this, options);

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
    },

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
    formatText(options) {
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
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.ReviewRequestFields.MultilineTextFieldView:
     *     This object, for chaining.
     */
    render() {
        Fields.TextFieldView.prototype.render.call(this);

        this.formatText();

        return this;
    },

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (object):
     *         The new value of the field.
     */
    formatValue(data) {
        if (this.allowRichText) {
            this.formatText({ newText: data });
        }
    },
});


/**
 * A field view for fields that include multiple comma-separated values.
 */
Fields.CommaSeparatedValuesTextFieldView = Fields.TextFieldView.extend({
    useEditIconOnly: true,

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
    _urlizeList(list, options={}) {
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
    },

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (Array):
     *         The new value of the field.
     */
    formatValue(data) {
        data = data || [];
        this.$el.html(data.join(', '));
    },
});


/**
 * A field view for checkbox fields.
 */
Fields.CheckboxFieldView = Fields.BaseFieldView.extend({
    /**
     * Render the field.
     *
     * Returns:
     *     RB.ReviewRequestFields.CheckboxFieldView:
     *     This object, for chaining.
     */
    render() {
        Fields.BaseFieldView.prototype.render.call(this);

        this.$el.change(() => {
            this._saveValue(this.$el.is(':checked'), {
                error: err => this.trigger('fieldError', err),
                success: () => this.trigger('fieldSaved'),
            });
        });

        return this;
    },
});


/**
 * A field view for dropdown fields.
 */
Fields.DropdownFieldView = Fields.BaseFieldView.extend({
    /**
     * Render the field.
     *
     * Returns:
     *     RB.ReviewRequestFields.DropdownFieldView:
     *     This object, for chaining.
     */
    render() {
        Fields.BaseFieldView.prototype.render.call(this);

        this.$el.change(() => {
            this._saveValue(this.$el.val(), {
                error: err => this.trigger('fieldError', err),
                success: () => this.trigger('fieldSaved'),
            });
        });

        return this;
    },
});


/**
 * A field view for date fields.
 */
Fields.DateFieldView = Fields.TextFieldView.extend({
    /**
     * Render the field.
     *
     * Returns:
     *     RB.ReviewRequestFields.DateFieldView:
     *     This object, for chaining.
     */
    render() {
        Fields.TextFieldView.prototype.render.call(this);

        this.inlineEditorView.$field
            .datepicker({
                changeMonth: true,
                changeYear: true,
                dateFormat: $.datepicker.ISO_8601,
                showButtonPanel: true,
                onSelect: (dateText, instance) => {
                    if (dateText !== instance.lastVal) {
                        this.inlineEditorView._dirty = true;
                    }
                },
            });

        return this;
    },

    /**
     * Save a new value for the field.
     *
     * Args:
     *     value (*):
     *         The new value for the field.
     *
     *     options (object):
     *         Options for the save operation.
     */
    _saveValue(value, options) {
        const m = moment(value, 'YYYY-MM-DD', true);

        if (!m.isValid()) {
            value = '';
            this.$el.text('');
        }

        Fields.TextFieldView.prototype._saveValue.call(this, value, options);
    },
});


/**
 * The "Branch" field.
 */
Fields.BranchFieldView = Fields.TextFieldView.extend({
    useExtraData: false,
});


/**
 * The "Bugs" field.
 */
Fields.BugsFieldView = Fields.CommaSeparatedValuesTextFieldView.extend({
    useExtraData: false,

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (Array):
     *         The new value of the field.
     */
    formatValue(data) {
        data = data || [];

        const reviewRequest = this.model.get('reviewRequest');
        const bugTrackerURL = reviewRequest.get('bugTrackerURL');

        if (bugTrackerURL) {
            this.$el
                .empty()
                .append(this._urlizeList(data, {
                    makeItemURL: item => bugTrackerURL.replace(
                        '--bug_id--', item),
                    cssClass: 'bug',
                }))
                .find('.bug').bug_infobox();
        } else {
            this.$el.text(data.join(', '));
        }
    },
});


/**
 * The change description field.
 */
Fields.ChangeDescriptionFieldView = Fields.MultilineTextFieldView.extend({
    allowRichText: true,
    jsonFieldName: 'changedescription',
    useExtraData: false,
});


/**
 * The commit list field.
 *
 * This provides expand/collapse functionality for commit messages that are
 * more than a single line.
 */
Fields.CommitListFieldView = Fields.BaseFieldView.extend({
    /**
     * Initialize the field.
     */
    initialize() {
        this._commitListView = null;
    },

    /**
     * Render the field.
     *
     * Returns:
     *     RB.ReviewRequestFields.CommitListFieldView:
     *     This view (for chaining).
     */
    render() {
        Fields.BaseFieldView.prototype.render.call(this);

        /*
         * We needn't render the view because it has already been rendered by
         * the server.
         */
        this._commitListView = new RB.DiffCommitListView({
            el: this.$('.commit-list'),
            model: new RB.DiffCommitList({
                commits: this.model.get('commits'),
                isInterdiff: false,
            }),
        });

        return this;
    },
});


/**
 * The close description field.
 */
Fields.CloseDescriptionFieldView = Fields.MultilineTextFieldView.extend({
    allowRichText: true,
    useExtraData: false,
    editableProp: 'statusEditable',

    /**
     * Save a new value for the field.
     *
     * Args:
     *     value (*):
     *         The new value for the field.
     *
     *     options (object):
     *         Options for the save operation.
     */
    _saveValue(value, options) {
        this.model.get('reviewRequest').close(_.defaults({
            type: this.closeType,
            description: value,
            postData: {
                force_text_type: 'html',
                include_text_types: 'raw',
            },
        }, options));
    },
});


/**
 * The "Depends On" field.
 */
Fields.DependsOnFieldView = Fields.CommaSeparatedValuesTextFieldView.extend({
    autocomplete: {
        fieldName: data => data.search.review_requests,
        nameKey: 'id',
        descKey: 'id',
        display_name: 'summary',
        resourceName: 'search',
        parseItem: item => {
            item.id = item.id.toString();
            item.display_name = item.summary;

            return item;
        },
        extraParams: {
            summary: 1,
        },
        cmp: (term, a, b) => b.data.id - a.data.id,
    },

    useEditIconOnly: true,
    useExtraData: false,

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (Array):
     *         The new value of the field.
     */
    formatValue(data) {
        data = data || [];

        this.$el
            .empty()
            .append(this._urlizeList(data, {
                makeItemURL: item => item.url,
                makeItemText: item => item.id,
                cssClass: 'review-request-link',
            }))
            .find('.review-request-link').review_request_infobox();
    },
});


/**
 * The "Description" field.
 */
Fields.DescriptionFieldView = Fields.MultilineTextFieldView.extend({
    allowRichText: true,
    useExtraData: false,
});


/**
 * The "Owner" field.
 */
Fields.OwnerFieldView = Fields.TextFieldView.extend({
    autocomplete: {
        fieldName: 'users',
        nameKey: 'username',
        descKey: 'fullname',
        extraParams: {
            fullname: 1,
        },
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
    },

    useEditIconOnly: true,
    useExtraData: false,

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (string):
     *         The new value of the field.
     */
    formatValue(data) {
        const $link = this._convertToLink(
            data,
            {
                makeItemURL: item => {
                    const href = item.href;
                    return href.substr(href.indexOf('/users'));
                },
                makeItemText: item => item.title,
                cssClass: 'user',
            });

        this.$el
            .empty()
            .append($link.user_infobox());
    }
});


/**
 * The "Summary" field.
 */
Fields.SummaryFieldView = Fields.TextFieldView.extend({
    useExtraData: false,
});


/**
 * The "Groups" field.
 */
Fields.TargetGroupsFieldView = Fields.CommaSeparatedValuesTextFieldView.extend({
    autocomplete: {
        fieldName: 'groups',
        nameKey: 'name',
        descKey: 'display_name',
        extraParams: {
            displayname: 1,
        },
    },

    useEditIconOnly: true,
    useExtraData: false,

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (Array):
     *         The new value of the field.
     */
    formatValue(data) {
        data = data || [];

        this.$el
            .empty()
            .append(this._urlizeList(data, {
                makeItemURL: item => item.url,
                makeItemText: item => item.name,
            }));
    },
});


/**
 * The "People" field.
 */
Fields.TargetPeopleFieldView = Fields.CommaSeparatedValuesTextFieldView.extend({
    autocomplete: {
        fieldName: 'users',
        nameKey: 'username',
        descKey: 'fullname',
        extraParams: {
            fullname: 1,
        },
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
    },

    useEditIconOnly: true,
    useExtraData: false,

    /**
     * Format the value into the field.
     *
     * Args:
     *     data (Array):
     *         The new value of the field.
     */
    formatValue(data) {
        data = data || [];
        this.$el
            .empty()
            .append(this._urlizeList(data, {
                makeItemURL: item => item.url,
                makeItemText: item => item.username,
                cssClass: 'user',
            }))
            .find('.user').user_infobox();
    }
});


/**
 * The "Testing Done" field.
 */
Fields.TestingDoneFieldView = Fields.MultilineTextFieldView.extend({
    allowRichText: true,
    useExtraData: false,
});


RB.ReviewRequestFields = Fields;


})();
