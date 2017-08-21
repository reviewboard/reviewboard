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
        Backbone.View.prototype.initialize.call(this, options);
        this.options = options;
        this.fieldID = options.fieldID;
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
        const inlineEditorOptions = {
            cls: `${this.$el.prop('id')}-editor`,
            editIconClass: 'rb-icon rb-icon-edit',
            enabled: this.model.get(this.editableProp),
            multiline: this.multiline,
            useEditIconOnly: this.useEditIconOnly,
            showRequiredFlag: this.$el.hasClass('required'),
            deferEventSetup: this.autocomplete !== null,
        };

        if (this.allowRichText) {
            const options = {
                useExtraData: this.useExtraData,
            };

            _.extend(
                inlineEditorOptions,
                RB.TextEditorView.getInlineEditorOptions({
                    minHeight: 0,
                    richText: this.model.getDraftField(
                        _.result(this, 'richTextAttr'), options),
                }),
                {
                    matchHeight: false,
                    hasRawValue: true,
                    rawValue: this.model.getDraftField(
                        fieldName, options) || '',
                });
        }

        this.$el
            .inlineEditor(inlineEditorOptions)
            .on({
                beginEdit: () => this.model.incr('editCount'),
                cancel: () => {
                    this.trigger('resize');
                    this.model.decr('editCount');
                },
                complete: (e, value) => {
                    this.trigger('resize');
                    this.model.decr('editCount');

                    const jsonFieldName = this.jsonFieldName || this.fieldID;
                    const extraOptions = { jsonFieldName, };

                    if (this.allowRichText) {
                        const textEditor =
                            RB.TextEditorView.getFromInlineEditor(this.$el);
                        extraOptions.richText = textEditor.richText;
                        extraOptions.jsonTextTypeFieldName = (
                            this.fieldID === 'text'
                            ? 'text_type'
                            : `${jsonFieldName}_text_type`);
                    }

                    this.model.setDraftField(
                        fieldName,
                        value,
                        _.defaults({
                            allowMarkdown: this.allowRichText,
                            closeType: this.closeType,
                            useExtraData: this.useExtraData,
                            error: err => {
                                this._formatField();
                                this.trigger('fieldError', err);
                            },
                            success: () => {
                                this._formatField();
                                this.trigger('fieldSaved');
                            }
                        }, extraOptions));
                },
                resize: () => this.trigger('resize'),
            });

        if (this.autocomplete !== null) {
            this._buildAutoComplete();
            this.$el.inlineEditor('setupEvents');
        }

        this.listenTo(
            this.model,
            `change:${this.editableProp}`,
            (model, editable) => this.$el.inlineEditor(
                editable ? 'enable': 'disable'));

        this.listenTo(this.model, `fieldChanged:${fieldName}`,
                      this._formatField);

        return this;
    },

    /**
     * Add auto-complete functionality to the field.
     */
    _buildAutoComplete() {
        const ac = this.autocomplete;
        const reviewRequest = this.model.get('reviewRequest');

        this.$el.inlineEditor('field')
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
        const value = this.model.getDraftField(
            _.result(this, 'fieldName'),
            { useExtraData: this.useExtraData });

        if (_.isFunction(this.formatValue)) {
            this.formatValue(value);
        } else {
            this.$el.text(value);
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
        Fields.BaseFieldView.prototype.initialize.call(this, options);

        /*
         * If this field is coming from an extension which doesn't specify any
         * JS-side version, we need to pull some data out of the markup.
         */
        if (this.allowRichText === null) {
            this.allowRichText = this.$el.data('allow-markdown');

            const reviewRequest = this.model.get('reviewRequest');
            const extraData = reviewRequest.draft.get('extraData');

            const rawValue = this.$el.data('raw-value');
            extraData[this.fieldID] = (rawValue !== undefined
                                       ? rawValue || ''
                                       : this.$el.text());
            this.$el.removeAttr('data-raw-value');

            if (this.allowRichText) {
                extraData[_.result(this, 'richTextAttr')] =
                    this.$el.hasClass('rich-text');
            }
        }
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

        this.reviewRequestEditorView.formatText(this.$el);

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
        // TODO: move formatText into this object.
        if (this.allowRichText) {
            this.reviewRequestEditorView.formatText(this.$el, {
                newText: data,
                fieldOptions: {
                    richTextAttr: _.result(this, 'richTextAttr'),
                },
            });
        }
    },
});


/**
 * A field view for fields that include multiple comma-separated values.
 */
Fields.CommaSeparatedValuesTextFieldView = Fields.TextFieldView.extend({
    useEditIconOnly: true,

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
                .append(this.reviewRequestEditorView.urlizeList(data, {
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
 * The close description field.
 */
Fields.CloseDescriptionFieldView = Fields.MultilineTextFieldView.extend({
    allowRichText: true,
    useExtraData: false,
    editableProp: 'statusEditable',
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
            .append(this.reviewRequestEditorView.urlizeList(data, {
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
 * The "Submitter" field.
 */
Fields.SubmitterFieldView = Fields.TextFieldView.extend({
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
        const $link = this.reviewRequestEditorView.convertToLink(
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
            .append(this.reviewRequestEditorView.urlizeList(data, {
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
            .append(this.reviewRequestEditorView.urlizeList(data, {
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
