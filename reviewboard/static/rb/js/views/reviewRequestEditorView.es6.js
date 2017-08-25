{


/**
 * Base class for review request banners.
 *
 * This will render a banner based on the data provided by subclasses,
 * and handle actions and editing of text fields.
 */
const BannerView = Backbone.View.extend({
    className: 'banner',
    title: '',
    subtitle: '',
    actions: [],
    showChangesField: true,
    describeText: '',
    fieldOptions: {},
    descriptionFieldID: 'changedescription',
    descriptionFieldName: null,
    descriptionFieldHTML: '',
    descriptionFieldClasses: '',
    showSendEmail: false,

    template: _.template(dedent`
        <h1><%- title %></h1>
        <% if (subtitle) { %>
        <p><%- subtitle %></p>
        <% } %>
        <span class="banner-actions">
        <% _.each(actions, function(action) { %>
         <input type="button" id="<%= action.id %>"
                value="<%- action.label %>" />
        <% }); %>
        <% if (showSendEmail) { %>
         <label>
          <input type="checkbox" class="send-email" checked />
          <%- sendEmailText %>
        </label>
        <% } %>
        </span>
        <% if (showChangesField) { %>
         <p><label for="field_changedescription">
        <%- describeText %></label></p>
         <pre id="field_changedescription"
              class="field field-text-area <%- descriptionFieldClasses %>"
              data-field-id="field_changedescription">
        <%= descriptionFieldHTML %></pre>
        <% } %>
        `),

    /**
     * Initialize the banner.
     *
     * Args:
     *     options (object):
     *         Options for the banner.
     *
     * Option Args:
     *     reviewRequestEditorView (RB.ReviewRequestEditorView):
     *         The review request editor.
     */
    initialize(options) {
        this.reviewRequestEditorView = options.reviewRequestEditorView;
        this.reviewRequestEditor = this.reviewRequestEditorView.model;
        this.reviewRequest = this.reviewRequestEditor.get('reviewRequest');

        this.reviewRequestEditorView.registerField(_.defaults({
            fieldID: this.descriptionFieldID,
            fieldName: this.descriptionFieldName,
            elementOptional: true,
            allowMarkdown: true,
            useExtraData: false,
            formatter: (view, data, $el, fieldOptions) => {
                view.formatText($el, {
                    newText: data,
                    fieldOptions: fieldOptions
                });
            },
        }, this.fieldOptions));

        this.$buttons = null;
    },

    /**
     * Render the banner.
     *
     * If there's an existing banner on the page, from the generated
     * template, then this will make use of that template. Otherwise,
     * it will construct a new one.
     *
     * Returns:
     *     BannerView:
     *     This object, for chaining.
     */
    render() {
        if (this.$el.children().length === 0) {
            this.$el.html(this.template({
                title: this.title,
                subtitle: this.subtitle,
                actions: this.actions,
                showChangesField: this.showChangesField,
                describeText: this.describeText,
                descriptionFieldHTML: this.descriptionFieldHTML,
                descriptionFieldClasses: this.descriptionFieldClasses,
                showSendEmail: this.showSendEmail,
                sendEmailText: gettext('Send E-Mail'),
            }));
        }

        this.$buttons = this.$('input');

        this.reviewRequestEditor.on(
            'saving destroying',
            () => this.$buttons.prop('disabled', true));

        this.reviewRequestEditor.on(
            'saved saveFailed destroyed',
            () => this.$buttons.prop('disabled', false));

        this.reviewRequestEditorView.setupFieldEditor(this.descriptionFieldID);

        return this;
    },
});


/**
 * Base class for a banner representing a closed review request.
 *
 * This provides a button for reopening the review request. It's up
 * to subclasses to provide the other details.
 */
const ClosedBannerView = BannerView.extend({
    descriptionFieldName: 'closeDescription',

    actions: [
        {
            id: 'btn-review-request-reopen',
            label: gettext('Reopen for Review'),
        },
    ],

    fieldOptions: {
        statusField: true,
    },

    events: {
        'click #btn-review-request-reopen': '_onReopenClicked',
    },

    /**
     * Render the banner.
     *
     * Returns:
     *     ClosedBannerView:
     *     This object, for chaining.
     */
    render() {
        const descriptionFieldClasses = [];

        if (this.reviewRequestEditor.get('statusMutableByUser')) {
            descriptionFieldClasses.push('editable');
        }

        if (this.reviewRequest.get('closeDescriptionRichText')) {
            descriptionFieldClasses.push('rich-text');
        }

        this.descriptionFieldClasses = descriptionFieldClasses.join(' ');
        this.descriptionFieldHTML =
            this.reviewRequestEditor.get('closeDescriptionRenderedText');

        return BannerView.prototype.render.apply(this, arguments);
    },

    /**
     * Handle a click on "Reopen for Review".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onReopenClicked() {
        this.reviewRequest.reopen({
            error: (model, xhr) => alert(xhr.errorText),
        });

        return false;
    },
});


/**
 * A banner representing a discarded review request.
 */
const DiscardedBannerView = ClosedBannerView.extend({
    id: 'discard-banner',
    title: gettext('This change has been discarded.'),
    describeText: gettext("Describe the reason it's discarded (optional):"),
    fieldOptions: _.defaults({
        closeType: RB.ReviewRequest.CLOSE_DISCARDED,
    }, ClosedBannerView.prototype.fieldOptions),
});


/**
 * A banner representing a submitted review request.
 */
const SubmittedBannerView = ClosedBannerView.extend({
    id: 'submitted-banner',
    title: gettext('This change has been marked as submitted.'),
    describeText: gettext('Describe the submission (optional):'),
    fieldOptions: _.defaults({
        closeType: RB.ReviewRequest.CLOSE_SUBMITTED,
    }, ClosedBannerView.prototype.fieldOptions),
});


/**
 * A banner representing a draft of a review request.
 *
 * Depending on the public state of the review request, this will
 * show different text and a different set of buttons.
 */
const DraftBannerView = BannerView.extend({
    id: 'draft-banner',
    title: gettext('This review request is a draft.'),
    subtitle: gettext('Be sure to publish when finished.'),
    describeText: gettext('Describe your changes (optional):'),
    descriptionFieldName: 'changeDescription',

    _newDraftTemplate: _.template(dedent`
        <div class="interdiff-link">
         <%- newDiffText %>
         <a href="<%- interdiffLink %>"><%- showChangesText %></a>
        </div>
        `),

    events: {
        'click #btn-draft-publish': '_onPublishDraftClicked',
        'click #btn-draft-discard': '_onDiscardDraftClicked',
        'click #btn-review-request-discard': '_onCloseDiscardedClicked',
    },

    /**
     * Initialize the banner.
     */
    initialize() {
        BannerView.prototype.initialize.apply(this, arguments);

        if (this.reviewRequest.get('public')) {
            this.showSendEmail = this.reviewRequestEditor.get('showSendEmail');
            this.title = gettext('This review request is a draft.');
            this.actions = [
                {
                    id: 'btn-draft-publish',
                    label: gettext('Publish Changes'),
                },
                {
                    id: 'btn-draft-discard',
                    label: gettext('Discard Draft'),
                },
            ];
        } else {
            this.showChangesField = false;
            this.actions = [
                {
                    id: 'btn-draft-publish',
                    label: gettext('Publish'),
                },
                {
                    id: 'btn-review-request-discard',
                    label: gettext('Discard Review Request'),
                },
            ];
        }
    },

    /**
     * Handle a click on "Publish Changes".
     *
     * Begins publishing the review request. If there are any field editors
     * still open, they'll be saved first.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onPublishDraftClicked() {
        const $sendEmail = this.$('.send-email');

        this.reviewRequestEditorView.publishDraft({
            trivial: ($sendEmail.length === 1 && !$sendEmail.is(':checked')),
        });

        return false;
    },

    /**
     * Handle a click on "Discard Draft".
     *
     * Discards the draft of the review request.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onDiscardDraftClicked() {
        this.reviewRequest.draft.destroy({
            error: xhr => alert(xhr.errorText),
        });

        return false;
    },

    /**
     * Handle a click on "Discard Review Request".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onCloseDiscardedClicked() {
        this.reviewRequest.close({
            type: RB.ReviewRequest.CLOSE_DISCARDED,
        });

        return false;
    },

    /**
     * Render the banner.
     *
     * Returns:
     *     DraftBannerView:
     *     This object, for chaining.
     */
    render() {
        const descriptionFieldClasses = [];

        if (this.reviewRequestEditor.get('mutableByUser')) {
            descriptionFieldClasses.push('editable');
        }

        const draft = this.reviewRequest.draft;

        if (draft.get('changeDescriptionRichText')) {
            descriptionFieldClasses.push('rich-text');
        }

        this.descriptionFieldClasses = descriptionFieldClasses.join(' ');
        this.descriptionFieldHTML =
            this.reviewRequestEditor.get('changeDescriptionRenderedText');

        BannerView.prototype.render.apply(this, arguments);

        const interdiffLink = draft.get('interdiffLink');

        if (interdiffLink) {
            this.$el.append(this._newDraftTemplate({
                newDiffText: gettext('This draft adds a new diff.'),
                showChangesText: gettext('Show changes'),
                interdiffLink: interdiffLink,
            }));
        }

        return this;
    },
});


/**
 * Manages the user-visible state of an editable review request.
 *
 * This owns the fields, thumbnails, banners, and general interaction
 * around editing a review request.
 */
RB.ReviewRequestEditorView = Backbone.View.extend({
    defaultFields: [
        {
            fieldID: 'branch',
        },
        {
            fieldID: 'bugs_closed',
            fieldName: 'bugsClosed',
            selector: '#field_bugs_closed',
            useEditIconOnly: true,
            formatter: (view, data, $el) => {
                const reviewRequest = view.model.get('reviewRequest');
                const bugTrackerURL = reviewRequest.get('bugTrackerURL');

                data = data || [];

                if (bugTrackerURL) {
                    $el
                        .empty()
                        .append(view.urlizeList(data, {
                            makeItemURL: item => bugTrackerURL.replace(
                                '--bug_id--', item),
                            cssClass: 'bug',
                        }))
                        .find('.bug').bug_infobox();
                } else {
                    $el.text(data.join(', '));
                }
            },
        },
        {
            fieldID: 'depends_on',
            fieldName: 'dependsOn',
            autocomplete: {
                fieldName: data => data.search.review_requests,
                nameKey: 'id',
                descKey: 'summary',
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
            formatter: (view, data, $el) => {
                $el
                    .empty()
                    .append(view.urlizeList(data, {
                        makeItemURL: item => item.url,
                        makeItemText: item => item.id,
                        cssClass: 'review-request-link',
                    }))
                    .find('.review-request-link').review_request_infobox();
            },
        },
        {
            fieldID: 'description',
            allowMarkdown: true,
            formatter: (view, data, $el, fieldOptions) => {
                view.formatText($el, {
                    newText: data,
                    fieldOptions: fieldOptions,
                });
            },
        },
        {
            fieldID: 'summary',
        },
        {
            fieldID: 'submitter',
            fieldName: 'submitter',
            useEditIconOnly: true,
            autocomplete: {
                fieldName: 'users',
                nameKey: 'username',
                descKey: 'fullname',
                extraParams: {
                    fullname: 1,
                },
                cmp: (term, a, b) => {
                    /*
                     * Sort the results with username matches first (in
                     * alphabetical order), followed by real name matches (in
                     * alphabetical order)
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
            formatter: (view, data, $el) => {
                const $link = view.convertToLink(
                    data,
                    {
                        makeItemURL: item => {
                            const href = item.href;
                            return href.substr(href.indexOf('/users'));
                        },
                        makeItemText: item => item.title,
                        cssClass: 'user',
                    });

                $el
                    .empty()
                    .append($link.user_infobox());
            },
        },
        {
            fieldID: 'target_groups',
            fieldName: 'targetGroups',
            useEditIconOnly: true,
            autocomplete: {
                fieldName: 'groups',
                nameKey: 'name',
                descKey: 'display_name',
                extraParams: {
                    displayname: 1,
                },
            },
            formatter: (view, data, $el) => {
                $el
                    .empty()
                    .append(view.urlizeList(data, {
                        makeItemURL: item => item.url,
                        makeItemText: item => item.name,
                    }));
            },
        },
        {
            fieldID: 'target_people',
            fieldName: 'targetPeople',
            useEditIconOnly: true,
            autocomplete: {
                fieldName: 'users',
                nameKey: 'username',
                descKey: 'fullname',
                extraParams: {
                    fullname: 1,
                },
                cmp: (term, a, b) => {
                    /*
                     * Sort the results with username matches first (in
                     * alphabetical order), followed by real name matches (in
                     * alphabetical order)
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
            formatter: (view, data, $el) => {
                $el
                    .empty()
                    .append(view.urlizeList(data, {
                        makeItemURL: item => item.url,
                        makeItemText: item => item.username,
                        cssClass: 'user',
                    }))
                    .find('.user').user_infobox();
            },
        },
        {
            fieldID: 'testing_done',
            fieldName: 'testingDone',
            allowMarkdown: true,
            formatter: (view, data, $el, fieldOptions) => {
                view.formatText($el, {
                    newText: data,
                    fieldOptions: fieldOptions,
                });
            },
        },
    ],

    events: {
        'click .has-menu .has-menu': '_onMenuClicked',
        'click #archive-review-request-link': '_onArchiveClicked',
        'click #unarchive-review-request-link': '_onUnarchiveClicked',
        'click #mute-review-request-link': '_onMuteClicked',
        'click #unmute-review-request-link': '_onUnmuteClicked',
    },

    _archiveActionsTemplate: _.template(dedent`
        <% if (visibility === RB.ReviewRequest.VISIBILITY_VISIBLE) { %>
         <li><a id="archive-review-request-link" href="#"><%- archiveText %></a></li>
         <li><a id="mute-review-request-link" href="#"><%- muteText %></a></li>
        <% } else if (visibility === RB.ReviewRequest.VISIBILITY_ARCHIVED) { %>
         <li><a id="unarchive-review-request-link" href="#"><%- unarchiveText %></a></li>
        <% } else if (visibility === RB.ReviewRequest.VISIBILITY_MUTED) { %>
         <li><a id="unmute-review-request-link" href="#"><%- unmuteText %></a></li>
        <% } %>
        `),

    /**
     * Initialize the view.
     */
    initialize() {
        _.bindAll(this, '_checkResizeLayout', '_scheduleResizeLayout',
                  '_onCloseDiscardedClicked', '_onCloseSubmittedClicked',
                  '_onDeleteReviewRequestClicked', '_onUpdateDiffClicked',
                  '_onArchiveClicked', '_onUnarchiveClicked',
                  '_onMuteClicked', '_onUnmuteClicked');

        this._fieldEditors = {};
        this._hasFields = (this.$('.editable').length > 0);

        if (this._hasFields) {
            _.each(
                this.defaultFields,
                fieldInfo => this.registerField(_.defaults({
                    useExtraData: false,
                }, fieldInfo)));
        }

        this.draft = this.model.get('reviewRequest').draft;
        this.banner = null;
        this._$main = null;
        this._$extra = null;
        this._blockResizeLayout = false;
    },

    /**
     * Register an editor for a field.
     *
     * Args:
     *     options (object):
     *         Options for the field editor.
     *
     * Option Args:
     *     fieldName (string):
     *         The name of the field in the model.
     *
     *     elementOptional (boolean, optional):
     *         True if the element does not have to already exist in the DOM.
     *
     *     formatter (function, optional):
     *         A function that formats the field in the model into HTML. If not
     *         provided, the contents of the field will be used as-is.
     *
     *     jsonFieldName (string, optional):
     *         The field name in the JSON payload. If not provided,
     *         ``fieldName`` will be used.
     *
     *     selector (string, optional):
     *         The jQuery selector for the element in the DOM. Defaults to
     *         ``#fieldName``.
     *
     *     useEditIconOnly (boolean, optional):
     *         If true, only clicking the edit icon will begin editing. If
     *         false, clicks on the field itself will also trigger an edit.
     *         Defaults to false.
     *
     *     useExtraData (boolean, optional):
     *         If true, field values will be stored in extraData instead of
     *         model attributes. Defaults to true for non-builtin fields.
     */
    registerField(options) {
        const fieldID = options.fieldID;

        console.assert(fieldID);

        const useExtraData = (options.useExtraData === undefined
                              ? true
                              : options.useExtraData);
        const jsonTextTypeFieldName = (fieldID === 'text'
                                       ? 'text_type'
                                       : fieldID + '_text_type');

        options = _.extend({
            selector: `#field_${fieldID}`,
            elementOptional: false,
            fieldID: fieldID,
            fieldName: fieldID,
            formatter: null,
            jsonFieldName: fieldID,
            jsonTextTypeFieldName: options.allowMarkdown ?
                                   jsonTextTypeFieldName
                                   : null,
            useEditIconOnly: false,
            useExtraData: useExtraData,
        }, options);

        // This must be done one we have a solid fieldName set.
        options.richTextAttr = options.allowMarkdown
                               ? options.fieldName + 'RichText'
                               : null;

        this._fieldEditors[fieldID] = options;
    },

    /**
     * Render the editor.
     *
     * This will import all pre-rendered file attachment and screenshot
     * thumbnails, turning them into FileAttachment and Screenshot objects.
     *
     * Returns:
     *     RB.ReviewRequestEditorView:
     *     This object, for chaining.
     */
    render() {
        const reviewRequest = this.model.get('reviewRequest');
        const fileAttachments = this.model.get('fileAttachments');
        const draft = reviewRequest.draft;
        const extraData = draft.get('extraData');

        this._$box = this.$('.review-request');
        this._$warning = $('#review-request-warning');
        this._$screenshots = $('#screenshot-thumbnails');
        this._$attachments = $('#file-list');
        this._$attachmentsContainer = $(this._$attachments.parent()[0]);
        this._$bannersContainer = $('#review-request-banners');
        this._$main = $('#review-request-main');
        this._$extra = $('#review-request-extra');

        this.listenTo(reviewRequest, 'change:visibility',
                      this._updateArchiveVisibility);
        this._updateArchiveVisibility();

        /*
         * Find any editors that weren't registered. These may be from
         * extensions.
         */
        if (this._hasFields) {
            _.each(this.$('.field.editable'), field => {
                const $field = $(field);
                const fieldID = $field.data('field-id');

                if (!this._fieldEditors[fieldID] &&
                    $field.hasClass('editable')) {

                    const fieldInfo = {
                        fieldID: fieldID,
                    };

                    const rawValue = $field.data('raw-value');

                    if (rawValue === undefined) {
                        extraData[fieldID] = $field.text();
                    } else {
                        extraData[fieldID] = rawValue || '';
                    }

                    $field.removeAttr('data-raw-value');

                    if ($field.data('allow-markdown')) {
                        fieldInfo.allowMarkdown = true;
                        const richTextFieldID = `${fieldID}RichText`;
                        extraData[richTextFieldID] =
                            $field.hasClass('rich-text');
                    }

                    if ($field.hasClass('comma-editable')) {
                        fieldInfo.useEditIconOnly = true;
                        fieldInfo.formatter = (view, data, $el) => {
                            data = data || [];
                            $el.html(data.join(', '));
                        };
                    } else if (fieldInfo.allowMarkdown) {
                        fieldInfo.formatter = (view, data, $el, options) => {
                            view.formatText($el, {
                                newText: data,
                                fieldOptions: options,
                            });
                        };
                    }

                    this.registerField(fieldInfo);
                }
            }, this);

            // Set up editors for every registered field.
            _.each(this._fieldEditors,
                   (fieldOptions, fieldID) => this.setupFieldEditor(fieldID));
        }

        /*
         * We need to show any banners before we continue with field setup,
         * since the banners register and set up fields as well.
         *
         * If we do this any later, formatText() will be called prematurely,
         * preventing proper Markdown text loading and saving from working
         * correctly.
         */
        this.showBanner();

        // Let's resume with the field setup now.
        if (this._hasFields) {
            /*
             * Linkify any text in the description, testing done, and change
             * description fields.
             *
             * Do this as soon as possible, so that we don't show spinners for
             * too long. It must be done after the fields are set up,
             * though.
             */
            _.each(this.$('.field-text-area'), el => this.formatText($(el)));

            if (this.model.get('editable')) {
                RB.DnDUploader.instance.registerDropTarget(
                    this._$attachmentsContainer,
                    gettext('Drop to add a file attachment'),
                    this._uploadFile.bind(this));
            }

            /*
             * Update the layout constraints any time these properties
             * change. Also, right away.
             */
            $(window).resize(this._scheduleResizeLayout);
            this.listenTo(this.model, 'change:editCount', this._checkResizeLayout);
            this._checkResizeLayout();

            $("#review-request-files-placeholder").remove();

            fileAttachments.each(
                fileAttachment => this.buildFileAttachmentThumbnail(
                    fileAttachment, fileAttachments, { noAnimation: true }));

            this.listenTo(fileAttachments, 'add', this.buildFileAttachmentThumbnail);
            this.listenTo(fileAttachments, 'destroy', () => {
                if (fileAttachments.length === 0) {
                    this._$attachmentsContainer.hide();
                }
            });

            /*
             * Import all the screenshots and file attachments rendered onto
             * the page.
             */
            _.each(this._$screenshots.find('.screenshot-container'),
                   this._importScreenshotThumbnail,
                   this);
            _.each($('.binary'),
                   this._importFileAttachmentThumbnail,
                   this);
        }

        this._setupActions();

        this.model.on('publishError', errorText => {
            alert(errorText);

            this.$('#btn-draft-publish').enable();
            this.$('#btn-draft-discard').enable();
        });

        this.model.on('closeError', errorText => alert(errorText));
        this.model.on('saved', this.showBanner, this);
        this.model.on('published', this._refreshPage, this);
        reviewRequest.on('closed reopened', this._refreshPage, this);
        draft.on('destroyed', this._refreshPage, this);

        window.onbeforeunload = this._onBeforeUnload.bind(this);

        return this;
    },

    /**
     * Warn the user if they try to navigate away with unsaved comments.
     *
     * Args:
     *     evt (Event):
     *         The event that triggered the handler.
     *
     * Returns:
     *     string:
     *     The warning message.
     *
     */
    _onBeforeUnload(evt) {
        if (this.model.get('editCount') > 0) {
            /*
             * On IE, the text must be set in evt.returnValue.
             *
             * On Firefox, it must be returned as a string.
             *
             * On Chrome, it must be returned as a string, but you
             * can't set it on evt.returnValue (it just ignores it).
             */
            const msg = gettext('You have unsaved changes that will be lost if you navigate away from this page.');
            evt = evt || window.event;

            evt.returnValue = msg;
            return msg;
        }
    },

    /**
     * Set up an editor for the given field.
     *
     * This will build the editor for a field and update the field contents
     * any time the matching field changes on a draft.
     *
     * Args:
     *     fieldID (string):
     *         The ID of the field to set up.
     */
    setupFieldEditor(fieldID) {
        const fieldOptions = this._fieldEditors[fieldID];
        const $el = this.$(fieldOptions.selector);

        if ($el.length === 0) {
            return;
        }

        this._buildEditor($el, fieldOptions);

        if (_.has(fieldOptions, 'autocomplete')) {
            this._buildAutoComplete($el, fieldOptions.autocomplete);
            $el.inlineEditor('setupEvents');
        }

        this.listenTo(this.model, `fieldChanged:${fieldOptions.fieldName}`,
                      this._formatField.bind(this, fieldOptions));
    },

    /**
     * Show a banner for the given state of the review request.
     */
    showBanner() {
        if (this.banner) {
            return;
        }

        const reviewRequest = this.model.get('reviewRequest');
        const state = reviewRequest.get('state');
        let BannerClass;

        if (state === RB.ReviewRequest.CLOSE_SUBMITTED) {
            BannerClass = SubmittedBannerView;
        } else if (state === RB.ReviewRequest.CLOSE_DISCARDED) {
            BannerClass = DiscardedBannerView;
        } else if (state === RB.ReviewRequest.PENDING &&
                   this.model.get('hasDraft')) {
            BannerClass = DraftBannerView;
        } else {
            return;
        }

        let $existingBanner = this._$bannersContainer.children();

        console.assert(BannerClass);
        console.assert($existingBanner.length <= 1);

        if ($existingBanner.length === 0) {
            $existingBanner = undefined;
        }

        this.banner = new BannerClass({
            el: $existingBanner,
            reviewRequestEditorView: this,
        });

        if ($existingBanner) {
            $existingBanner.show();
        } else {
            this.banner.$el.appendTo(this._$bannersContainer);
        }

        this.banner.render();
    },

    /**
     * Handle a click on the "Publish Draft" button.
     *
     * Begins publishing the review request. If there are any field editors
     * still open, they'll be saved first.
     *
     * Args:
     *     options (object):
     *         Options for the publish operation.
     */
    publishDraft(options) {
        // Save all the fields if we need to.
        const fields = this.$(".editable:inlineEditorDirty");

        this.model.set({
            publishing: true,
            pendingSaveCount: fields.length,
        });

        if (fields.length === 0) {
            this.model.publishDraft(options);
        } else {
            fields.inlineEditor('submit');
        }
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
    convertToLink(item, options={}) {
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
    urlizeList(list, options={}) {
        let $links = $();

        if (list) {
            const len = list.length;

            for (let i = 0; i < len; i++) {
                $links = $links.add(this.convertToLink(list[i], options));

                if (i < len - 1) {
                    $links = $links.add(new Text(', '));
                }
            }
        }

        return $links;
    },

    /**
     * Linkify a block of text.
     *
     * This turns URLs, /r/#/ paths, and bug numbers into clickable links. It's
     * a wrapper around RB.formatText that handles passing in the bug tracker.
     */
    formatText($el, options) {
        const reviewRequest = this.model.get('reviewRequest');

        options = _.defaults({
            bugTrackerURL: reviewRequest.get('bugTrackerURL'),
            isHTMLEncoded: true
        }, options);

        const fieldOptions = options.fieldOptions;

        if (fieldOptions && fieldOptions.richTextAttr) {
            options.richText = this.model.getDraftField(
                fieldOptions.richTextAttr,
                fieldOptions);
        }

        RB.formatText($el, options);

        $el.find('img').load(this._checkResizeLayout);
    },

    /**
     * Upload a dropped file as a file attachment.
     *
     * A temporary file attachment placeholder will appear while the
     * file attachment uploads. After the upload has finished, it will
     * be replaced with the thumbnail depicting the file attachment.
     *
     * Args:
     *     file (File):
     *         The file to upload.
     */
    _uploadFile(file) {
        // Create a temporary file listing.
        const fileAttachment = this.model.createFileAttachment();

        fileAttachment.set('file', file);
        fileAttachment.save();
    },

    /**
     * Set up all review request actions and listens for events.
     */
    _setupActions() {
        const $closeDiscarded = this.$('#discard-review-request-action');
        const $closeSubmitted = this.$('#submit-review-request-action');
        const $deletePermanently = this.$('#delete-review-request-action');
        const $updateDiff = this.$('#upload-diff-action');

        /*
         * We don't want the click event filtering from these down to the
         * parent menu, so we can't use events above.
         */
        $closeDiscarded.click(this._onCloseDiscardedClicked);
        $closeSubmitted.click(this._onCloseSubmittedClicked);
        $deletePermanently.click(this._onDeleteReviewRequestClicked);
        $updateDiff.click(this._onUpdateDiffClicked);

        RB.ReviewRequestActionHook.each(hook => {
            _.each(hook.get('callbacks'),
                   (selector, handler) => this.$(selector).click(handler));
        });
    },

    /**
     * Build a thumbnail for a FileAttachment.
     *
     * The thumbnail will eb added to the page. The editor will listen
     * for events on the thumbnail to update the current edit state.
     *
     * This can be called either when dynamically adding a new file
     * attachment (through drag-and-drop or Add File), or after importing
     * from the rendered page.
     *
     * Args:
     *     fileAttachment (RB.FileAttachment):
     *         The file attachment.
     *
     *     collection (Backbone.Collection):
     *         The collection of all file attachments.
     *
     *     options (object):
     *         Options.
     *
     * Option Args:
     *     $el (jQuery):
     *         The thumbnail element, if it already exists in the DOM.
     */
    buildFileAttachmentThumbnail(fileAttachment, collection, options={}) {
        const fileAttachmentComments = this.model.get('fileAttachmentComments');
        const $thumbnail = options.$el;

        const view = new RB.FileAttachmentThumbnail({
            el: $thumbnail,
            model: fileAttachment,
            comments: fileAttachmentComments[fileAttachment.id],
            renderThumbnail: ($thumbnail === undefined),
            reviewRequest: this.model.get('reviewRequest'),
            canEdit: (this.model.get('editable') === true)
        });

        view.render();

        if (!$thumbnail) {
            // This is a newly added file attachment.
            this._$attachmentsContainer.show();
            view.$el.insertBefore(this._$attachments.children('br'));

            if (!options.noAnimation) {
                view.fadeIn();
            }
        }

        this.listenTo(view, 'hoverIn', $thumbnail => {
            this._$attachments
                .find('.file')
                .not($thumbnail.find('.file')[0])
                    .addClass('faded');
        });

        this.listenTo(
            view, 'hoverOut',
            () => this._$attachments.find('.file').removeClass('faded'));

        view.on('beginEdit', () => this.model.incr('editCount'));
        view.on('endEdit', () => this.model.decr('editCount'));
        view.on('commentSaved', () => RB.DraftReviewBannerView.instance.show());
    },

    /**
     * Import file attachments from the rendered page.
     *
     * Each file attachment already rendered will be turned into a
     * FileAttachment, and a new thumbnail will be built for it.
     *
     * Args:
     *     thumbnailEl (Element):
     *         The existing DOM element to import.
     */
    _importFileAttachmentThumbnail(thumbnailEl) {
        const $thumbnail = $(thumbnailEl);
        const id = $thumbnail.data('file-id');
        const $caption = $thumbnail.find('.file-caption .edit');
        const reviewRequest = this.model.get('reviewRequest');
        const fileAttachment = reviewRequest.draft.createFileAttachment({
            id: id,
        });

        if (!$caption.hasClass('empty-caption')) {
            fileAttachment.set('caption', $caption.text());
        }

        this.model.get('fileAttachments').add(fileAttachment, {
            $el: $thumbnail,
        });
    },

    /**
     * Import screenshots from the rendered page.
     *
     * Each screenshot already rendered will be turned into a Screenshot.
     *
     * Args:
     *     thumbnailEl (Element):
     *         The existing DOM element to import.
     */
    _importScreenshotThumbnail(thumbnailEl) {
        const $thumbnail = $(thumbnailEl);
        const id = $thumbnail.data('screenshot-id');
        const reviewRequest = this.model.get('reviewRequest');
        const screenshot = reviewRequest.createScreenshot(id);
        const view = new RB.ScreenshotThumbnail({
            el: $thumbnail,
            model: screenshot,
        });

        view.render();

        this.model.get('screenshots').add(screenshot);

        view.on('beginEdit', () => this.model.incr('editCount'));
        view.on('endEdit', () => this.model.decr('editCount'));
    },

    /**
     * Add inline editing capabilities to a field for a review request.
     *
     * Args:
     *     $el (jQuery):
     *         The field element.
     *
     *     fieldOptions (object):
     *         Options for the field editor.
     */
    _buildEditor($el, fieldOptions) {
        const model = this.model;
        const el = $el[0];
        const id = el.id;
        const editableProp = (fieldOptions.statusField
                              ? 'statusEditable'
                              : 'editable');
        const multiline = $el.hasClass('field-text-area');
        const options = {
            cls: `${id}-editor`,
            editIconClass: 'rb-icon rb-icon-edit',
            enabled: this.model.get(editableProp),
            multiline: multiline,
            useEditIconOnly: fieldOptions.useEditIconOnly,
            showRequiredFlag: $el.hasClass('required'),
            deferEventSetup: _.has(fieldOptions, 'autocomplete'),
        };

        if (fieldOptions.allowMarkdown) {
            _.extend(
                options,
                RB.TextEditorView.getInlineEditorOptions({
                    minHeight: 0,
                    richText: model.getDraftField(fieldOptions.richTextAttr,
                                                  fieldOptions),
                }),
                {
                    matchHeight: false,
                    hasRawValue: true,
                    rawValue: model.getDraftField(fieldOptions.fieldName,
                                                  fieldOptions) || '',
                });
        }

        $el
            .inlineEditor(options)
            .on({
                beginEdit: () => model.incr('editCount'),
                cancel: () => {
                    this._scheduleResizeLayout();
                    model.decr('editCount');
                },
                complete: (e, value) => {
                    const extraOptions = {};

                    if (fieldOptions.allowMarkdown) {
                        const textEditor =
                            RB.TextEditorView.getFromInlineEditor($el);
                        extraOptions.richText = textEditor.richText;
                    }

                    this._scheduleResizeLayout();
                    model.decr('editCount');
                    model.setDraftField(
                        fieldOptions.fieldName,
                        value,
                        _.defaults({
                            error: error => {
                                this._formatField(fieldOptions);
                                this._$warning
                                    .delay(6000)
                                    .fadeOut(400, function() {
                                        $(this).hide();
                                    })
                                    .show()
                                    .html(error.errorText);
                            },
                            success: () => {
                                this._formatField(fieldOptions);
                                this.showBanner();
                            },
                        }, fieldOptions, extraOptions),
                        this);
                },
                resize: this._checkResizeLayout,
            });

        this.listenTo(
            this.model, `change:${editableProp}`,
            (model, editable) => $el.inlineEditor(
                editable ? 'enable' : 'disable'));
    },

    /**
     * Add auto-complete functionality to a field.
     *
     * Args:
     *     $el (jQuery):
     *         The field element.
     *
     *     options (object):
     *         Options for the auto-complete.
     *
     * Option Args:
     *     fieldName (string):
     *         The field name (``groups`` or ``people``).
     *
     *     nameKey (string):
     *         The key containing the item name in the result data.
     *
     *     descKey (string, optional):
     *         The key containing the item description in the result data.
     *
     *     extraParams (object, optional):
     *         Extra parameters to send in the query.
     */
    _buildAutoComplete($el, options) {
        const reviewRequest = this.model.get('reviewRequest');

        $el.inlineEditor('field')
            .rbautocomplete({
                formatItem: data => {
                    let s = data[options.nameKey];

                    if (options.descKey && data[options.descKey]) {
                        s += ' <span>(' + _.escape(data[options.descKey]) +
                             ')</span>';
                    }

                    return s;
                },
                matchCase: false,
                multiple: true,
                parse: data => {
                    const parsed = [];
                    let items;

                    if (_.isFunction(options.fieldName)) {
                        items = options.fieldName(data);
                    } else {
                        items = data[options.fieldName];
                    }

                    for (let i = 0; i < items.length; i++) {
                        let item = items[i];

                        if (options.parseItem) {
                            item = options.parseItem(item);
                        }

                        parsed.push({
                            data: item,
                            value: item[options.nameKey],
                            result: item[options.nameKey],
                        });
                    }

                    return parsed;
                },
                url: SITE_ROOT + reviewRequest.get('localSitePrefix') +
                     'api/' + (options.resourceName || options.fieldName) + '/',
                extraParams: options.extraParams,
                cmp: options.cmp,
                width: 350,
                error: xhr => {
                    let text;

                    try {
                        text = $.parseJSON(xhr.responseText).err.msg;
                    } catch (e) {
                        text = 'HTTP ' + xhr.status + ' ' + xhr.statusText;
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
     * Conditionally resize the layout.
     *
     * This is a wrapper for _resizeLayout that verifies that there's actually
     * a layout to resize.
     */
    _checkResizeLayout() {
        /*
         * Not every page that uses this has a #review-request-main element
         * (for instance, review UIs want to have the draft banners but not
         * the review request box). In this case, just skip all of this.
         */
        if (this._$main.length !== 0 && !this._blockResizeLayout) {
            this._resizeLayout();
        }
    },

    /**
     * Resize the layout in response to size or position changes of fields.
     *
     * This will spread out the main text fields to cover the full height of
     * the review request box's main area. That helps keep a consistent look
     * and prevents a bunch of wasted-looking space.
     */
    _resizeLayout() {
        const $lastContent = this._$main.children('.review-request-section:last-child');
        const $lastFieldContainer = $lastContent.children('.field-container');
        const $lastEditable = $lastFieldContainer.children('.editable');
        const lastContentTop = Math.ceil($lastContent.position().top);
        const editor = $lastEditable.inlineEditor('field').data('text-editor');
        const detailsWidth = 300; // Defined as @details-width in reviews.less
        const detailsPadding = 10;
        const $detailsBody = $('#review-request-details tbody');
        const $detailsLabels = $detailsBody.find('th:first-child');
        const $detailsValues = $detailsBody.find('span');

        this._blockResizeLayout = true;

        /*
         * Make sure that the details fields wrap correctly, even if they don't
         * have wrappable characters (this combines with the white-space:
         * word-wrap: break-word style). This computation makes things handle
         * potentially unknown field labels correctly.
         */
        $detailsValues.css('max-width', (detailsWidth -
                                         $detailsLabels.outerWidth() -
                                         detailsPadding * 3) + 'px');

        /*
         * Reset all the heights so we can do calculations based on their
         * native sizes.
         */
        this._$main.height('auto');
        $lastContent.height('auto');
        $lastEditable.height('auto');

        if (editor) {
            editor.setSize(null, 'auto');
        }

        /*
         * Set the review request box's main height to take up the full
         * amount of spaces between its top and the top of the "extra"
         * pane (where the issue summary table and stuff live).
         */
        this._$main.height(this._$extra.offset().top -
                           this._$main.offset().top);
        const height = this._$main.height();

        if ($lastContent.outerHeight() + lastContentTop < height) {
            $lastContent.outerHeight(height - lastContentTop);

            /*
             * Get the size of the content box, and factor in the padding at
             * the bottom, to balance out position()'s calculation of the
             * padding at the top. This ensures we get a height that matches
             * the content area of the content box.
             */
            const contentHeight = $lastContent.height() -
                                  Math.ceil($lastFieldContainer.position().top);

            /*
             * Set the height of the editor or the editable field placeholder,
             * depending on whether we're in edit mode. There's no need to do
             * both, since this logic will be called again when the state
             * changes.
             */
            if ($lastEditable.inlineEditor('editing') && editor) {
                editor.setSize(
                    null,
                    contentHeight -
                    $lastEditable.inlineEditor('buttons').height());
            } else {
                /*
                 * It's possible to squish the editable element if we force
                 * a size, so make sure it's always at least the natural
                 * height.
                 */
                const newEditableHeight = contentHeight +
                                          $lastEditable.getExtents('m', 'tb');

                if (newEditableHeight > $lastEditable.outerHeight()) {
                    $lastEditable.outerHeight(newEditableHeight);
                }
            }
        }

        this._blockResizeLayout = false;
    },

    /**
     * Schedule a layout resize after the stack unwinds.
     *
     * This will only trigger a layout resize after the stack has unwound,
     * and only once every 100 milliseconds at most.
     */
    _scheduleResizeLayout: _.throttleLayout(
        function() { this._checkResizeLayout(); },
        { defer: true, }),

    /**
     * Format the contents of a field.
     *
     * If there's a registered field formatter for this field, it will
     * be used to display the contents of a field in the draft.
     *
     * Args:
     *     fieldOptions (object):
     *         Options for the field.
     *
     * Option Args:
     *     selector (string):
     *         A selector to find the field element.
     *
     *     formatter (function, optional):
     *         A function that formats the data into HTML.
     *
     *     context (object, optional):
     *         Optional context to use when calling ``formatter``.
     */
    _formatField(fieldOptions) {
        const formatter = fieldOptions.formatter;
        const $el = this.$(fieldOptions.selector);
        const value = this.model.getDraftField(fieldOptions.fieldName,
                                               fieldOptions);

        if (_.isFunction(formatter)) {
            formatter.call(fieldOptions.context || this, this, value, $el,
                           fieldOptions);
        } else {
            $el.text(value);
        }
    },

    /**
     * Handle a click on "Close -> Discarded".
     *
     * The user will be asked for confirmation before the review request is
     * discarded.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onCloseDiscardedClicked() {
        const confirmText = gettext(
            "Are you sure you want to discard this review request?");

        if (confirm(confirmText)) {
            this.model.get('reviewRequest').close({
                type: RB.ReviewRequest.CLOSE_DISCARDED,
                error: (model, xhr) => this.model.trigger(
                    'closeError', xhr.errorText),
            });
        }

        return false;
    },

    /**
     * Handle a click on "Close -> Submitted".
     *
     * If there's an unpublished draft, this will first confirm if the
     * user is sure.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onCloseSubmittedClicked() {
        /*
         * This is a non-destructive event, so don't confirm unless there's
         * a draft.
         */
        let submit = true;

        if (this.banner) {
            submit = confirm(gettext("You have an unpublished draft. If you close this review request, the draft will be discarded. Are you sure you want to close the review request?"));
        }

        if (submit) {
            this.model.get('reviewRequest').close({
                type: RB.ReviewRequest.CLOSE_SUBMITTED,
                error: (model, xhr) => this.model.trigger(
                    'closeError', xhr.errorText),
            });
        }

        return false;
    },

    /**
     * Handle a click on "Close -> Delete Permanently".
     *
     * The user will be asked for confirmation before the review request is
     * deleted.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onDeleteReviewRequestClicked() {
        const $dlg = $('<p>')
            .text(gettext('This deletion cannot be undone. All diffs and reviews will be deleted as well.'))
            .modalBox({
                title: gettext('Are you sure you want to delete this review request?'),
                buttons: [
                    $(`<input type="button" value="${gettext('Cancel')}"/>`),
                    $(`<input type="button" value="${gettext('Delete')}"/>`)
                        .click(() => {
                            this.model.get('reviewRequest').destroy({
                                buttons: $('input', $dlg.modalBox('buttons')),
                                success: () => {
                                    window.location = SITE_ROOT;
                                },
                            });
                        }),
                ]
            });

        return false;
    },

    /**
     * Handle a click on "Update -> Update Diff".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onUpdateDiffClicked() {
        const reviewRequest = this.model.get('reviewRequest');
        const updateDiffView = new RB.UpdateDiffView({
            model: new RB.UploadDiffModel({
                changeNumber: reviewRequest.get('commitID'),
                repository: reviewRequest.get('repository'),
                reviewRequest: reviewRequest,
            }),
        });

        updateDiffView.render();

        return false;
    },

    /**
     * Handle a click on "Archive -> Archive".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onArchiveClicked() {
        return this._updateArchiveState(
            RB.UserSession.instance.archivedReviewRequests,
            true,
            RB.ReviewRequest.VISIBILITY_ARCHIVED);
    },

    /**
     * Handle a click on "Archive -> Unarchive".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onUnarchiveClicked() {
        return this._updateArchiveState(
            RB.UserSession.instance.archivedReviewRequests,
            false,
            RB.ReviewRequest.VISIBILITY_VISIBLE);
    },

    /**
     * Handle a click on "Archive -> Mute".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onMuteClicked() {
        return this._updateArchiveState(
            RB.UserSession.instance.mutedReviewRequests,
            true,
            RB.ReviewRequest.VISIBILITY_MUTED);
    },

    /**
     * Handle a click on "Archive -> Unmute".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onUnmuteClicked() {
        return this._updateArchiveState(
            RB.UserSession.instance.mutedReviewRequests,
            false,
            RB.ReviewRequest.VISIBILITY_VISIBLE);
    },

    /**
     * Update archive/mute state.
     *
     * Args:
     *     collection (Backbone.Collection):
     *         The collection representing the user's archived or muted review
     *         requests.
     *
     *     add (boolean):
     *         True if the review request should be added to the collection
     *         (archived or muted), false if it shold be removed (unarchived or
     *         unmuted).
     *
     *     newState (number):
     *         The new state for the review request's ``visibility`` attribute.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _updateArchiveState(collection, add, newState) {
        const reviewRequest = this.model.get('reviewRequest');
        const options = {
            success: () => reviewRequest.set('visibility', newState),
        };

        if (add) {
            collection.addImmediately(reviewRequest, options, this);
        } else {
            collection.removeImmediately(reviewRequest, options, this);
        }

        return false;
    },

    /**
     * Update the visibility of the archive/mute menu items.
     */
    _updateArchiveVisibility() {
        const visibility = this.model.get('reviewRequest').get('visibility');

        this.$('#hide-review-request-menu').html(this._archiveActionsTemplate({
            visibility: visibility,
            archiveText: gettext('Archive'),
            muteText: gettext('Mute'),
            unarchiveText: gettext('Unarchive'),
            unmuteText: gettext('Unmute'),
        }));

        const iconClass = (visibility === RB.ReviewRequest.VISIBILITY_VISIBLE
                           ? 'rb-icon-archive-off' : 'rb-icon-archive-on');

        this.$('#hide-review-request-link')
            .html(`<span class="rb-icon ${iconClass}"></span>`);
    },

    /**
     * Generic handler for menu clicks.
     *
     * This simply prevents the click from bubbling up or invoking the
     * default action.  This function is used for dropdown menu titles
     * so that their links do not send a request to the server when one
     * of their dropdown actions are clicked.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onMenuClicked() {
        return false;
    },

    /**
     * Refresh the page.
     */
    _refreshPage() {
        window.location = this.model.get('reviewRequest').get('reviewURL');
    },
});


}
