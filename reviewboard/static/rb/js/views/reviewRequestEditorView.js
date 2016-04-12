(function() {


var BannerView,
    ClosedBannerView,
    DraftBannerView;


/*
 * Base class for review request banners.
 *
 * This will render a banner based on the data provided by subclasses,
 * and handle actions and editing of text fields.
 */
BannerView = Backbone.View.extend({
    className: 'banner',
    title: '',
    subtitle: '',
    actions: [],
    showChangesField: true,
    describeText: '',
    fieldOptions: {},
    descriptionFieldID: 'changedescription',
    descriptionFieldName: null,

    template: _.template([
        '<h1><%- title %></h1>',
        '<%- subtitle %>',
        '<% _.each(actions, function(action) { %>',
        ' <input type="button" id="<%= action.id %>" ',
        '        value="<%- action.label %>" />',
        '<% }); %>',
        '<% if (showChangesField) { %>',
        ' <p><label for="field_changedescription">',
        '<%- describeText %></label></p>',
        ' <pre id="field_changedescription"',
        '      class="editable field-text-area field"',
        '      data-field-id="changedescription">',
        '<%- closeDescription %></pre>',
        '<% } %>'
    ].join('')),

    /*
     * Initializes the banner.
     */
    initialize: function(options) {
        this.reviewRequestEditorView = options.reviewRequestEditorView;
        this.reviewRequest =
            this.reviewRequestEditorView.model.get('reviewRequest');

        this.reviewRequestEditorView.registerField(_.defaults({
            fieldID: this.descriptionFieldID,
            fieldName: this.descriptionFieldName,
            elementOptional: true,
            allowMarkdown: true,
            useExtraData: false,
            formatter: function(view, data, $el, fieldOptions) {
                view.formatText($el, {
                    newText: data,
                    fieldOptions: fieldOptions
                });
            }
        }, this.fieldOptions));

        this.$buttons = null;
    },

    /*
     * Renders the banner.
     *
     * If there's an existing banner on the page, from the generated
     * template, then this will make use of that template. Otherwise,
     * it will construct a new one.
     */
    render: function() {
        var reviewRequestEditor = this.reviewRequestEditorView.model;

        if (this.$el.children().length === 0) {
            this.$el.html(this.template({
                title: this.title,
                subtitle: this.subtitle,
                actions: this.actions,
                showChangesField: this.showChangesField,
                describeText: this.describeText,
                closeDescription: this.reviewRequest.get('closeDescription')
            }));
        }

        this.$buttons = this.$('input');

        reviewRequestEditor.on('saving destroying', function() {
            this.$buttons.prop('disabled', true);
        }, this);

        reviewRequestEditor.on('saved saveFailed destroyed', function() {
            this.$buttons.prop('disabled', false);
        }, this);

        this.reviewRequestEditorView.setupFieldEditor(this.descriptionFieldID);

        return this;
    }
});


/*
 * Base class for a banner representing a closed review request.
 *
 * This provides a button for reopening the review request. It's up
 * to subclasses to provide the other details.
 */
ClosedBannerView = BannerView.extend({
    descriptionFieldName: 'closeDescription',

    actions: [
        {
            id: 'btn-review-request-reopen',
            label: gettext('Reopen for Review')
        }
    ],

    fieldOptions: {
        statusField: true
    },

    events: {
        'click #btn-review-request-reopen': '_onReopenClicked'
    },

    /*
     * Handler for Reopen Review Request.
     */
    _onReopenClicked: function() {
        this.reviewRequest.reopen({
            error: function(model, xhr) {
                alert(xhr.errorText);
            }
        });

        return false;
    }
});


/*
 * A banner representing a discarded review request.
 */
DiscardedBannerView = ClosedBannerView.extend({
    id: 'discard-banner',
    title: gettext('This change has been discarded.'),
    describeText: gettext("Describe the reason it's discarded (optional):"),
    fieldOptions: _.defaults({
        closeType: RB.ReviewRequest.CLOSE_DISCARDED
    }, ClosedBannerView.prototype.fieldOptions)
});


/*
 * A banner representing a submitted review request.
 */
SubmittedBannerView = ClosedBannerView.extend({
    id: 'submitted-banner',
    title: gettext('This change has been marked as submitted.'),
    describeText: gettext('Describe the submission (optional):'),
    fieldOptions: _.defaults({
        closeType: RB.ReviewRequest.CLOSE_SUBMITTED
    }, ClosedBannerView.prototype.fieldOptions)
});


/*
 * A banner representing a draft of a review request.
 *
 * Depending on the public state of the review request, this will
 * show different text and a different set of buttons.
 */
DraftBannerView = BannerView.extend({
    id: 'draft-banner',
    subtitle: 'Be sure to publish when finished.',
    describeText: 'Describe your changes (optional):',
    descriptionFieldName: 'changeDescription',

    events: {
        'click #btn-draft-publish': '_onPublishDraftClicked',
        'click #btn-draft-discard': '_onDiscardDraftClicked',
        'click #btn-review-request-discard': '_onCloseDiscardedClicked'
    },

    /*
     * Initializes the banner.
     */
    initialize: function() {
        _super(this).initialize.apply(this, arguments);

        if (this.reviewRequest.get('public')) {
            this.title = 'This review request is a draft.';
            this.actions = [
                {
                    id: 'btn-draft-publish',
                    label: gettext('Publish Changes')
                },
                {
                    id: 'btn-draft-discard',
                    label: gettext('Discard Draft')
                }
            ];
        } else {
            this.showChangesField = false;
            this.actions = [
                {
                    id: 'btn-draft-publish',
                    label: gettext('Publish')
                },
                {
                    id: 'btn-review-request-discard',
                    label: gettext('Discard Review Request')
                }
            ];
        }
    },

    /*
     * Handler for when the Publish Draft button is clicked.
     *
     * Begins publishing the review request. If there are any field editors
     * still open, they'll be saved first.
     */
    _onPublishDraftClicked: function() {
        this.reviewRequestEditorView.publishDraft();

        return false;
    },

    /*
     * Handler for when the Discard Draft button is clicked.
     *
     * Discards the draft of the review request.
     */
    _onDiscardDraftClicked: function() {
        this.reviewRequest.draft.destroy({
            error: function(xhr) {
                alert(xhr.errorText);
            }
        });

        return false;
    },

    /*
     * Handler for when Discard Review request button is clicked.
     */
    _onDiscardedReviewRequestClicked: function() {
        this.reviewRequestEditorView.closeDiscarded();

        return false;
    },

    /*
     * Handler for when Discard button is clicked.
     */
    _onCloseDiscardedClicked: function() {
        this.reviewRequest.close({
            type: RB.ReviewRequest.CLOSE_DISCARDED
        });

        return false;
    }
});


/*
 * Manages the user-visible state of an editable review request.
 *
 * This owns the fields, thumbnails, banners, and general interaction
 * around editing a review request.
 */
RB.ReviewRequestEditorView = Backbone.View.extend({
    defaultFields: [
        {
            fieldID: 'branch'
        },
        {
            fieldID: 'bugs_closed',
            fieldName: 'bugsClosed',
            selector: '#field_bugs_closed',
            useEditIconOnly: true,
            formatter: function(view, data, $el) {
                var reviewRequest = view.model.get('reviewRequest'),
                    bugTrackerURL = reviewRequest.get('bugTrackerURL');

                data = data || [];

                if (bugTrackerURL) {
                    $el.html(view.urlizeList(data, function(item) {
                        return bugTrackerURL.replace('%s', item);
                    }, _.escape));
                } else {
                    $el.text(data.join(", "));
                }
            }
        },
        {
            fieldID: 'depends_on',
            fieldName: 'dependsOn',
            useEditIconOnly: true,
            formatter: function(view, data, $el) {
                $el.html(view.urlizeList(
                    data,
                    function(item) { return item.url; },
                    function(item) { return item.id; }
                ));
            }
        },
        {
            fieldID: 'description',
            allowMarkdown: true,
            formatter: function(view, data, $el, fieldOptions) {
                view.formatText($el, {
                    newText: data,
                    fieldOptions: fieldOptions
                });
            }
        },
        {
            fieldID: 'summary'
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
                    displayname: 1
                }
            },
            formatter: function(view, data, $el) {
                $el.html(view.urlizeList(
                    data,
                    function(item) { return item.url; },
                    function(item) { return item.name; }
                ));
            }
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
                    fullname: 1
                },
                cmp: function(term, a, b) {
                    /*
                     * Sort the results with username matches first (in
                     * alphabetical order), followed by real name matches (in
                     * alphabetical order)
                     */
                    var aUsername = a.data.username,
                        bUsername = b.data.username,
                        aFullname = a.data.fullname,
                        bFullname = a.data.fullname;

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
                }
            },
            formatter: function(view, data, $el) {
                var $list = $(view.urlizeList(
                    data,
                    function(item) { return item.url; },
                    function(item) { return item.username; }
                ));

                $el.html(
                    $list
                        .addClass("user")
                        .user_infobox());
            }
        },
        {
            fieldID: 'testing_done',
            fieldName: 'testingDone',
            allowMarkdown: true,
            formatter: function(view, data, $el, fieldOptions) {
                view.formatText($el, {
                    newText: data,
                    fieldOptions: fieldOptions
                });
            }
        }
    ],

    initialize: function() {
        var $issueSummary = $('#issue-summary');

        _.bindAll(this, '_checkResizeLayout', '_scheduleResizeLayout');

        this._fieldEditors = {};
        this._hasFields = (this.$('.editable').length > 0);

        if (this._hasFields) {
            _.each(this.defaultFields, function(fieldInfo) {
                this.registerField(_.defaults({
                    useExtraData: false
                }, fieldInfo));
            }, this);
        }

        this.draft = this.model.get('reviewRequest').draft;
        this.banner = null;
        this._$main = null;
        this._$extra = null;
        this._blockResizeLayout = false;

        if ($issueSummary.length > 0) {
            this.issueSummaryTableView = new RB.IssueSummaryTableView({
                el: $('#issue-summary'),
                model: this.model.get('commentIssueManager')
            });
        }
    },

    /*
     * Registers an editor for a field.
     *
     * This will take a set of options for the editor.
     *
     * Required:
     *
     *     * fieldName
     *       - The name of the field in the model. This is required.
     *
     * Optional:
     *
     *     * elementOptional
     *       - true if the element doesn't have to be on the page.
     *
     *     * formatter
     *       - A function that formats the field in the model into HTML.
     *         Defaults to null.
     *
     *     * jsonFieldName
     *       - The field name in the JSON payload. Defaults to fieldName.
     *
     *     * selector
     *       - The jQuery selector for the element in the DOM.
     *         Defaults to '#' + fieldName.
     *
     *     * useEditIconOnly
     *       - If true, only clicking the edit icon will begin editing.
     *         Defaults to false.
     *
     *     * useExtraData
     *       - If true, field values will be stored in extraData.
     *         Defaults to true for non-builtin fields.
     */
    registerField: function(options) {
        var fieldID = options.fieldID,
            useExtraData = options.useExtraData === undefined
                           ? true
                           : options.useExtraData;

        console.assert(fieldID);

        options = _.extend({
            selector: '#field_' + fieldID,
            elementOptional: false,
            fieldID: fieldID,
            fieldName: fieldID,
            formatter: null,
            jsonFieldName: fieldID,
            jsonTextTypeFieldName: options.allowMarkdown ?
                                   fieldID + '_text_type'
                                   : null,
            useEditIconOnly: false,
            useExtraData: useExtraData
        }, options);

        /*
         * This must be done one we have a solid fieldName set.
         */
        options.richTextAttr = options.allowMarkdown
                               ? options.fieldName + 'RichText'
                               : null;

        this._fieldEditors[fieldID] = options;
    },

    /*
     * Renders the editor.
     *
     * This will import all pre-rendered file attachment and screenshot
     * thumbnails, turning them into FileAttachment and Screenshot objects.
     */
    render: function() {
        var reviewRequest = this.model.get('reviewRequest'),
            draft = reviewRequest.draft,
            extraData = draft.get('extraData');

        this._$box = this.$('.review-request');
        this._$warning = $('#review-request-warning');
        this._$screenshots = $('#screenshot-thumbnails');
        this._$attachments = $('#file-list');
        this._$attachmentsContainer = $(this._$attachments.parent()[0]);
        this._$bannersContainer = $('#review_request_banners');
        this._$main = $('#review_request_main');
        this._$extra = $('#review_request_extra');

        /*
         * Find any editors that weren't registered. These may be from
         * extensions.
         */
        if (this._hasFields) {
            _.each(this.$('.field.editable'), function(field) {
                var $field = $(field),
                    fieldID = $field.data('field-id'),
                    isCommaEditable,
                    richTextFieldID,
                    fieldInfo,
                    rawValue;

                if (!this._fieldEditors[fieldID] &&
                    $field.hasClass('editable')) {
                    isCommaEditable = $field.hasClass('comma-editable');

                    fieldInfo = {
                        fieldID: fieldID
                    };

                    rawValue = $field.data('raw-value');

                    if (rawValue === undefined) {
                        extraData[fieldID] = $field.text();
                    } else {
                        extraData[fieldID] = rawValue || '';
                    }

                    $field.removeAttr('data-raw-value');

                    if ($field.data('allow-markdown')) {
                        fieldInfo.allowMarkdown = true;

                        if (fieldID === 'text') {
                            richTextFieldID = 'rich_text';
                        } else {
                            richTextFieldID = fieldID + '_rich_text';
                        }

                        extraData[richTextFieldID] =
                            $field.hasClass('rich-text');
                    }

                    if (isCommaEditable) {
                        fieldInfo.useEditIconOnly = true;
                        fieldInfo.formatter = function(view, data, $el) {
                            data = data || [];
                            $el.html(data.join(', '));
                        };
                    } else if (fieldInfo.allowMarkdown) {
                        fieldInfo.formatter = function(view, data, $el,
                                                       fieldOptions) {
                            view.formatText($el, {
                                newText: data,
                                fieldOptions: fieldOptions
                            });
                        };
                    }

                    this.registerField(fieldInfo);
                }
            }, this);

            /*
             * Set up editors for every registered field.
             */
            _.each(this._fieldEditors, function(fieldOptions, fieldID) {
                this.setupFieldEditor(fieldID);
            }, this);
        }

        /*
         * We need to show any banners before we continue with field setup,
         * since the banners register and set up fields as well.
         *
         * If we do this any later, formatText() will be called prematurely,
         * preventing proper Markdown text loading and saving from working
         * correctly.
         */
        if (this._$bannersContainer.children().filter(':visible').length > 0) {
            this.showBanner();
        }

        /*
         * Let's resume with the field setup now.
         */
        if (this._hasFields) {
            /*
             * Linkify any text in the description, testing done, and change
             * description fields.
             *
             * Do this as soon as possible, so that we don't show spinners for
             * too long. It must be done after the fields are set up,
             * though.
             */
            _.each(this.$('.field-text-area'), function(el) {
                this.formatText($(el));
            }, this);

            if (this.model.get('editable')) {
                this.dndUploader = new RB.DnDUploader({
                    reviewRequestEditor: this.model
                });
            }

            /*
             * Update the layout constraints any time these properties
             * change. Also, right away.
             */
            $(window).resize(this._scheduleResizeLayout);
            this.listenTo(this.model, 'change:editCount', this._checkResizeLayout);
            this._checkResizeLayout();

            if (this.issueSummaryTableView) {
                this.issueSummaryTableView.render();
            }

            this.model.fileAttachments.on('add',
                                          this.buildFileAttachmentThumbnail,
                                          this);

            /*
             * Import all the screenshots and file attachments rendered onto
             * the page.
             */
            _.each(this._$screenshots.find('.screenshot-container'),
                   this._importScreenshotThumbnail,
                   this);
            _.each(this._$attachments.find('.file-container'),
                   this._importFileAttachmentThumbnail,
                   this);
            _.each($('.binary'),
                   this._importFileAttachmentThumbnail,
                   this);
        }

        this._setupActions();

        this.model.on('publishError', function(errorText) {
            alert(errorText);

            this.$('#btn-draft-publish').enable();
            this.$('#btn-draft-discard').enable();
        }, this);

        this.model.on('closeError', function(errorText) {
            alert(errorText);
        }, this);

        this.model.on('saved', this.showBanner, this);
        this.model.on('published', this._refreshPage, this);
        reviewRequest.on('closed reopened', this._refreshPage, this);
        draft.on('destroyed', this._refreshPage, this);

        /*
         * Warn the user if they try to navigate away with unsaved comments.
         */
        window.onbeforeunload = _.bind(function(evt) {
            if ((this.model.get('editable') ||
                 this.model.get('statusEditable')) &&
                this.model.get('editCount') > 0) {
                /*
                 * On IE, the text must be set in evt.returnValue.
                 *
                 * On Firefox, it must be returned as a string.
                 *
                 * On Chrome, it must be returned as a string, but you
                 * can't set it on evt.returnValue (it just ignores it).
                 */
                var msg = gettext("You have unsaved changes that will be lost if you navigate away from this page.");
                evt = evt || window.event;

                evt.returnValue = msg;
                return msg;
            }
        }, this);

        return this;
    },

    /*
     * Sets up an editor for the given field.
     *
     * This will build the editor for a field and update the field contents
     * any time the matching field changes on a draft.
     */
    setupFieldEditor: function(fieldID) {
        var fieldOptions = this._fieldEditors[fieldID],
            $el = this.$(fieldOptions.selector),
            listenObj;

        if ($el.length === 0) {
            return;
        }

        this._buildEditor($el, fieldOptions);

        if (_.has(fieldOptions, 'autocomplete')) {
            this._buildAutoComplete($el, fieldOptions.autocomplete);
            $el.inlineEditor('setupEvents');
        }

        this.listenTo(this.model, 'fieldChanged:' + fieldOptions.fieldName,
                      _.bind(this._formatField, this, fieldOptions));
    },

    /*
     * Shows a banner for the given state of the review request.
     */
    showBanner: function() {
        var BannerClass,
            reviewRequest = this.model.get('reviewRequest'),
            state = reviewRequest.get('state'),
            $existingBanner = this._$bannersContainer.children();

        if (this.banner) {
            return;
        }

        console.assert($existingBanner.length <= 1);

        if ($existingBanner.length === 0) {
            $existingBanner = undefined;
        }

        if (state === RB.ReviewRequest.CLOSE_SUBMITTED) {
            BannerClass = SubmittedBannerView;
        } else if (state === RB.ReviewRequest.CLOSE_DISCARDED) {
            BannerClass = DiscardedBannerView;
        } else if (state === RB.ReviewRequest.PENDING) {
            BannerClass = DraftBannerView;
        }

        console.assert(BannerClass);

        this.banner = new BannerClass({
            el: $existingBanner,
            reviewRequestEditorView: this
        });

        if ($existingBanner) {
            $existingBanner.show();
        } else {
            this.banner.$el.appendTo(this._$bannersContainer);
        }

        this.banner.render();
    },

    /*
     * Handler for when the Publish Draft button is clicked.
     *
     * Begins publishing the review request. If there are any field editors
     * still open, they'll be saved first.
     */
    publishDraft: function() {
        /* Save all the fields if we need to. */
        var fields = this.$(".editable:inlineEditorDirty");

        this.model.set({
            publishing: true,
            pendingSaveCount: fields.length
        });

        if (fields.length === 0) {
            this.model.publishDraft();
        } else {
            fields.inlineEditor("submit");
        }
    },

    /*
     * Converts an array of items to a list of hyperlinks.
     *
     * By default, this will use the item as the URL and as the hyperlink text.
     * By overriding urlFunc and textFunc, the URL and text can be customized.
     */
    urlizeList: function(list, urlFunc, textFunc) {
        var str = '',
            len,
            item,
            i;

        if (!list) {
            return '';
        }

        len = list.length;

        for (i = 0; i < len; i++) {
            item = list[i];

            str += '<a href="';
            str += (urlFunc ? urlFunc(item) : item);
            str += '">';
            str += (textFunc ? textFunc(item) : item);
            str += '</a>';

            if (i < len - 1) {
                str += ', ';
            }
        }

        return str;
    },

    /*
     * Linkifies a block of text, turning URLs, /r/#/ paths, and bug numbers
     * into clickable links.
     *
     * This is a wrapper around RB.formatText that handles passing in the bug
     * tracker.
     */
    formatText: function($el, options) {
        var reviewRequest = this.model.get('reviewRequest'),
            fieldOptions;

        options = _.defaults({
            bugTrackerURL: reviewRequest.get('bugTrackerURL'),
            isHTMLEncoded: true
        }, options);

        fieldOptions = options.fieldOptions;

        if (fieldOptions && fieldOptions.richTextAttr) {
            options.richText = this.model.getDraftField(
                fieldOptions.richTextAttr,
                fieldOptions);
        }

        RB.formatText($el, options);

        $el.find('img').load(this._checkResizeLayout);
    },

    /*
     * Sets up all review request actions and listens for events.
     */
    _setupActions: function() {
        var $closeDiscarded = this.$('#discard-review-request-link'),
            $closeSubmitted = this.$('#link-review-request-close-submitted'),
            $deletePermanently = this.$('#delete-review-request-link'),
            $menuitem;

        /* Provide support for expanding submenus in the action list. */
        function showMenu() {
            if ($menuitem) {
                $menuitem.children('ul').fadeOut('fast');
                $menuitem = null;
            }

            $(this).children('ul').fadeIn('fast');
        }

        function hideMenu() {
            $menuitem = $(this);

            setTimeout(function() {
                if ($menuitem) {
                    $menuitem.children('ul').fadeOut('fast');
                }
            }, 400);
        }

        this.$(".actions > li:has(ul.menu)")
            .hover(showMenu, hideMenu)
            .toggle(showMenu, hideMenu);

        /*
         * We don't want the click event filtering from these down to the
         * parent menu, so we can't use events above.
         */
        $closeDiscarded.click(_.bind(this._onCloseDiscardedClicked, this));
        $closeSubmitted.click(_.bind(this._onCloseSubmittedClicked, this));
        $deletePermanently.click(_.bind(this._onDeleteReviewRequestClicked,
                                        this));
    },

    /*
     * Builds a thumbnail for a FileAttachment.
     *
     * The thumbnail will eb added to the page. The editor will listen
     * for events on the thumbnail to update the current edit state.
     *
     * This can be called either when dynamically adding a new file
     * attachment (through drag-and-drop or Add File), or after importing
     * from the rendered page.
     */
    buildFileAttachmentThumbnail: function(fileAttachment, collection,
                                           options) {
        var fileAttachmentComments = this.model.get('fileAttachmentComments'),
            $thumbnail,
            view;

        options = options || {};

        $thumbnail = options.$el;

        view = new RB.FileAttachmentThumbnail({
            el: $thumbnail,
            model: fileAttachment,
            comments: fileAttachmentComments[fileAttachment.id],
            renderThumbnail: ($thumbnail === undefined),
            reviewRequest: this.model.get('reviewRequest'),
            canEdit: (this.model.get('editable') === true)
        });

        view.render();

        if (!$thumbnail) {
            /* This is a newly added file attachment. */
            this._$attachmentsContainer.show();
            view.$el.insertBefore(this._$attachments.children('br'));
            view.fadeIn();
        }

        view.on('beginEdit', function() {
            this.model.incr('editCount');
        }, this);

        view.on('endEdit', function() {
            this.model.decr('editCount');
        }, this);

        view.on('commentSaved', function() {
            RB.DraftReviewBannerView.instance.show();
        }, this);
    },

    /*
     * Imports file attachments from the rendered page.
     *
     * Each file attachment already rendered will be turned into a
     * FileAttachment, and a new thumbnail will be built for it.
     */
    _importFileAttachmentThumbnail: function(thumbnailEl) {
        var $thumbnail = $(thumbnailEl),
            id = $thumbnail.data('file-id'),
            $caption = $thumbnail.find('.file-caption .edit'),
            reviewRequest = this.model.get('reviewRequest'),
            fileAttachment = reviewRequest.draft.createFileAttachment({
                id: id
            });

        if (!$caption.hasClass('empty-caption')) {
            fileAttachment.set('caption', $caption.text());
        }

        this.model.fileAttachments.add(fileAttachment, {
            $el: $thumbnail
        });
    },

    /*
     * Imports screenshots from the rendered page.
     *
     * Each screenshot already rendered will be turned into a Screenshot.
     */
    _importScreenshotThumbnail: function(thumbnailEl) {
        var $thumbnail = $(thumbnailEl),
            id = $thumbnail.data('screenshot-id'),
            reviewRequest = this.model.get('reviewRequest'),
            screenshot = reviewRequest.createScreenshot(id),
            view = new RB.ScreenshotThumbnail({
                el: $thumbnail,
                model: screenshot
            });

        view.render();

        this.model.screenshots.add(screenshot);

        view.on('beginEdit', function() {
            this.model.incr('editCount');
        }, this);

        view.on('endEdit', function() {
            this.model.decr('editCount');
        }, this);
    },

    /*
     * Adds inline editing capabilities to a field for a review request.
     */
    _buildEditor: function($el, fieldOptions) {
        var model = this.model,
            el = $el[0],
            id = el.id,
            editableProp = (fieldOptions.statusField
                            ? 'statusEditable'
                            : 'editable'),
            multiline = $el.hasClass('field-text-area'),
            options = {
                cls: id + '-editor',
                editIconClass: 'rb-icon rb-icon-edit',
                enabled: this.model.get(editableProp),
                multiline: multiline,
                useEditIconOnly: fieldOptions.useEditIconOnly,
                showRequiredFlag: $el.hasClass('required'),
                deferEventSetup: _.has(fieldOptions, 'autocomplete')
            };

        if (fieldOptions.allowMarkdown) {
            _.extend(
                options,
                RB.TextEditorView.getInlineEditorOptions({
                    minHeight: 0,
                    richText: model.getDraftField(fieldOptions.richTextAttr,
                                                  fieldOptions)
                }),
                {
                    matchHeight: false,
                    hasRawValue: true,
                    rawValue: model.getDraftField(fieldOptions.fieldName,
                                                  fieldOptions) || ''
                });
        }

        $el
            .inlineEditor(options)
            .on({
                beginEdit: function() {
                    model.incr('editCount');
                },
                cancel: _.bind(function() {
                    this._scheduleResizeLayout();
                    model.decr('editCount');
                }, this),
                complete: _.bind(function(e, value) {
                    var extraOptions = {},
                        textEditor;

                    if (fieldOptions.allowMarkdown) {
                        textEditor =
                            RB.TextEditorView.getFromInlineEditor($el);

                        extraOptions.richText = textEditor.richText;
                    }

                    this._scheduleResizeLayout();
                    model.decr('editCount');
                    model.setDraftField(
                        fieldOptions.fieldName,
                        value,
                        _.defaults({
                            error: function(error) {
                                this._formatField(fieldOptions);
                                this._$warning
                                    .delay(6000)
                                    .fadeOut(400, function() {
                                        $(this).hide();
                                    })
                                    .show()
                                    .html(error.errorText);
                            },
                            success: function() {
                                this._formatField(fieldOptions);
                                this.showBanner();
                            }
                        }, fieldOptions, extraOptions),
                        this);
                }, this),
                resize: this._checkResizeLayout
            });

        this.listenTo(
            this.model,
            'change:' + editableProp,
            function(model, editable) {
                $el.inlineEditor(editable ? 'enable' : 'disable');
            });
    },

    /*
     * Adds auto-complete functionality to a field.
     *
     * options expects the following fields:
     *
     *    fieldName   - The field name ("groups" or "people").
     *    nameKey     - The key containing the name in the result data.
     *    descKey     - The key containing the description in the result
     *                  data. This is optional.
     *    extraParams - Extra parameters to send in the query. This is optional.
     */
    _buildAutoComplete: function($el, options) {
        var reviewRequest = this.model.get('reviewRequest');

        $el.inlineEditor('field')
            .rbautocomplete({
                formatItem: function(data) {
                    var s = data[options.nameKey];

                    if (options.descKey && data[options.descKey]) {
                        s += ' <span>(' + _.escape(data[options.descKey]) +
                             ')</span>';
                    }

                    return s;
                },
                matchCase: false,
                multiple: true,
                parse: function(data) {
                    var items = data[options.fieldName],
                        itemsLen = items.length,
                        parsed = [],
                        value,
                        i;

                    for (i = 0; i < itemsLen; i++) {
                        value = items[i];

                        parsed.push({
                            data: value,
                            value: value[options.nameKey],
                            result: value[options.nameKey]
                        });
                    }

                    return parsed;
                },
                url: SITE_ROOT + reviewRequest.get('localSitePrefix') +
                     'api/' + (options.resourceName || options.fieldName) + '/',
                extraParams: options.extraParams,
                cmp: options.cmp,
                width: 350,
                error: function(xhr) {
                    var text;

                    try {
                        text = $.parseJSON(xhr.responseText).err.msg;
                    } catch (e) {
                        text = 'HTTP ' + xhr.status + ' ' + xhr.statusText;
                    }

                    alert(text);
                }
            })
            .on('autocompleteshow', function() {
                /*
                 * Add the footer to the bottom of the results pane the
                 * first time it's created.
                 *
                 * Note that we may have multiple .ui-autocomplete-results
                 * elements, and we don't necessarily know which is tied to
                 * this. So, we'll look for all instances that don't contain
                 * a footer.
                 */
                var resultsPane = $('.ui-autocomplete-results:not(' +
                                    ':has(.ui-autocomplete-footer))');

                if (resultsPane.length > 0) {
                    $('<div/>')
                        .addClass('ui-autocomplete-footer')
                        .text(gettext('Press Tab to auto-complete.'))
                        .appendTo(resultsPane);
                }
            });
    },

    /*
     * Wrapper for _resizeLayout that verifies that there's actually a layout
     * to resize.
     */
    _checkResizeLayout: function() {
        /*
         * Not every page that uses this has a #review_request_main element
         * (for instance, review UIs want to have the draft banners but not
         * the review request box). In this case, just skip all of this.
         */
        if (this._$main.length !== 0 && !this._blockResizeLayout) {
            this._resizeLayout();
        }
    },

    /*
     * Resizes the layout in response to size or position changes of fields.
     *
     * This will spread out the main text fields to cover the full height of
     * the review request box's main area. That helps keep a consistent look
     * and prevents a bunch of wasted-looking space.
     */
    _resizeLayout: function() {
        var $lastContent = this._$main.children('.content:last-child'),
            $lastFieldContainer = $lastContent.children('.field-container'),
            $lastEditable = $lastFieldContainer.children('.editable'),
            lastContentTop = Math.ceil($lastContent.position().top),
            editor = $lastEditable.inlineEditor('field').data('text-editor'),
            detailsWidth = 300, // Defined as @details-width in reviews.less
            detailsPadding = 10,
            $detailsBody = $('#review_request_details tbody'),
            $detailsLabels = $detailsBody.find('th:first-child'),
            $detailsValues = $detailsBody.find('span'),
            contentHeight,
            newEditableHeight,
            height;

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
        this._$main.outerHeight(this._$extra.offset().top -
                                this._$main.offset().top);
        height = this._$main.height();

        if ($lastContent.outerHeight() + lastContentTop < height) {
            $lastContent.outerHeight(height - lastContentTop);

            /*
             * Get the size of the content box, and factor in the padding at
             * the bottom, to balance out position()'s calculation of the
             * padding at the top. This ensures we get a height that matches
             * the content area of the content box.
             */
            contentHeight = $lastContent.height() +
                            $lastContent.getExtents('p', 't') -
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
                    $lastEditable.inlineEditor('buttons').outerHeight(true));
            } else {
                /*
                 * It's possible to squish the editable element if we force
                 * a size, so make sure it's always at least the natural
                 * height.
                 */
                newEditableHeight = contentHeight +
                                    $lastEditable.getExtents('m', 'tb');

                if (newEditableHeight > $lastEditable.outerHeight()) {
                    $lastEditable.outerHeight(newEditableHeight);
                }
            }
        }

        this._blockResizeLayout = false;
    },

    /*
     * Schedules a layout resize after the stack unwinds.
     *
     * This will only trigger a layout resize after the stack has unwound,
     * and only once every 100 milliseconds at most.
     */
    _scheduleResizeLayout: _.throttle(function() {
        _.defer(this._checkResizeLayout);
    }, 100),

    /*
     * Formats the contents of a field.
     *
     * If there's a registered field formatter for this field, it will
     * be used to display the contents of a field in the draft.
     */
    _formatField: function(fieldOptions) {
        var formatter = fieldOptions.formatter,
            $el = this.$(fieldOptions.selector),
            value = this.model.getDraftField(fieldOptions.fieldName,
                                             fieldOptions);

        if (_.isFunction(formatter)) {
            formatter.call(fieldOptions.context || this, this, value, $el,
                           fieldOptions);
        } else {
            $el.text(value);
        }
    },

    /*
     * Handler for when Close -> Discarded is clicked.
     *
     * The user will be asked for confirmation before the review request is
     * discarded.
     */
    _onCloseDiscardedClicked: function() {
        var confirmText = gettext(
            "Are you sure you want to discard this review request?");

        if (confirm(confirmText)) {
            this.model.get('reviewRequest').close({
                type: RB.ReviewRequest.CLOSE_DISCARDED,
                error: function(model, xhr) {
                    this.model.trigger('closeError', xhr.errorText);
                }
            }, this);
        }

        return false;
    },

    /*
     * Handler for when Close -> Submitted is clicked.
     *
     * If there's an unpublished draft, this will first confirm if the
     * user is sure.
     */
    _onCloseSubmittedClicked: function() {
        /*
         * This is a non-destructive event, so don't confirm unless there's
         * a draft.
         */
        var submit = true;

        if (this.banner) {
            submit = confirm(gettext("You have an unpublished draft. If you close this review request, the draft will be discarded. Are you sure you want to close the review request?"));
        }

        if (submit) {
            this.model.get('reviewRequest').close({
                type: RB.ReviewRequest.CLOSE_SUBMITTED,
                error: function(model, xhr) {
                    this.model.trigger('closeError', xhr.errorText);
                }
            }, this);
        }

        return false;
    },

    /*
     * Handler for Close -> Delete Permanently.
     *
     * The user will be asked for confirmation before the review request is
     * deleted.
     */
    _onDeleteReviewRequestClicked: function() {
        var dlg = $("<p/>")
            .text(gettext("This deletion cannot be undone. All diffs and reviews will be deleted as well."))
            .modalBox({
                title: gettext("Are you sure you want to delete this review request?"),
                buttons: [
                    $('<input type="button" value="' + gettext('Cancel') + '"/>'),
                    $('<input type="button" value="' + gettext('Delete') + '"/>')
                        .click(_.bind(function() {
                            this.model.get('reviewRequest').destroy({
                                buttons: $("input", dlg.modalBox("buttons")),
                                success: function() {
                                    window.location = SITE_ROOT;
                                }
                            });
                        }, this))
                ]
            });

        return false;
    },

    _refreshPage: function() {
        window.location = this.model.get('reviewRequest').get('reviewURL');
    }
});


})();
