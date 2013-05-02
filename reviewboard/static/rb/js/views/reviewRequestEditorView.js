/*
 * Manages the user-visible state of an editable review request.
 *
 * This owns the fields, thumbnails, banners, and general interaction
 * around editing a review request.
 */
RB.ReviewRequestEditorView = Backbone.View.extend({
    events: {
        'click #btn-draft-publish': '_onPublishDraftClicked',
        'click #btn-draft-discard': '_onDiscardDraftClicked',
        'click #btn-review-request-discard': '_onCloseDiscardedClicked',
        'click #btn-review-request-reopen': '_onReopenClicked'
    },

    defaultFields: [
        {
            fieldName: 'branch'
        },
        {
            fieldName: 'bugsClosed',
            jsonFieldName: 'bugs_closed',
            elementID: 'bugs_closed',
            useEditIconOnly: true,
            formatter: function(view, data) {
                var reviewRequest = view.model.get('reviewRequest'),
                    bugTrackerURL = reviewRequest.get('bugTrackerURL');

                data = data || [];

                if (!bugTrackerURL) {
                    return data.join(", ");
                }

                return view.urlizeList(data, function(item) {
                    return bugTrackerURL.replace('%s', item);
                });
            }
        },
        {
            fieldName: 'changeDescription',
            elementID: 'changedescription',
            jsonFieldName: 'changedescription',
            elementOptional: true,
            startOpen: true
        },
        {
            fieldName: 'description',
            formatter: function(view, data) {
                return view.linkifyText(data);
            }
        },
        {
            fieldName: 'summary'
        },
        {
            fieldName: 'targetGroups',
            elementID: 'target_groups',
            jsonFieldName: 'target_groups',
            useEditIconOnly: true,
            autocomplete: {
                fieldName: 'groups',
                nameKey: 'name',
                descKey: 'display_name',
                extraParams: {
                    displayname: 1
                }
            },
            formatter: function(view, data) {
                return view.urlizeList(
                    data,
                    function(item) { return item.url; },
                    function(item) { return item.name; }
                );
            }
        },
        {
            fieldName: 'targetPeople',
            elementID: 'target_people',
            jsonFieldName: 'target_people',
            useEditIconOnly: true,
            autocomplete: {
                fieldName: 'users',
                nameKey: 'username',
                descKey: 'fullname',
                extraParams: {
                    fullname: 1
                }
            },
            formatter: function(view, data) {
                var $list = $(view.urlizeList(
                    data,
                    function(item) { return item.url; },
                    function(item) { return item.username; }
                ));

                return $list
                    .addClass("user")
                    .user_infobox();
            }
        },
        {
            fieldName: 'testingDone',
            elementID: 'testing_done',
            jsonFieldName: 'testing_done',
            formatter: function(view, data) {
                return view.linkifyText(data);
            }
        }
    ],

    initialize: function() {
        this._fieldEditors = {};

        _.each(this.defaultFields, this.registerField, this);
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
     *     * elementID
     *       - The ID of the element in the DOM. Defaults to fieldName.
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
     *     * startOpen
     *       - Field starts opened in edit mode.
     *         Defaults to false.
     *
     *     * useEditIconOnly
     *       - If true, only clicking the edit icon will begin editing.
     *         Defaults to false.
     */
    registerField: function(options) {
        console.assert(_.has(options, 'fieldName'));

        this._fieldEditors[options.fieldName] = _.extend({
            elementID: options.fieldName,
            elementOptional: false,
            formatter: null,
            jsonFieldName: options.fieldName,
            startOpen: false,
            useEditIconOnly: false
        }, options);
    },

    /*
     * Renders the editor.
     *
     * This will import all pre-rendered file attachment and screenshot
     * thumbnails, turning them into FileAttachment and Screenshot objects.
     */
    render: function() {
        var draft = this.model.get('reviewRequest').draft,
            $closeDiscarded = this.$('#discard-review-request-link'),
            $closeSubmitted = this.$('#link-review-request-close-submitted'),
            $deletePermanently = this.$('#delete-review-request-link');

        this.$draftBanner = $('#draft-banner');
        this.$draftBannerButtons = this.$draftBanner.find('input');

        this._$warning = $('#review-request-warning');
        this._$screenshots = $('#screenshot-thumbnails');
        this._$attachments = $('#file-list');
        this._$attachmentsContainer = $(this._$attachments.parent()[0]);

        /*
         * We don't want the click event filtering from these down to the
         * parent menu, so we can't use events above.
         */
        $closeDiscarded.click(_.bind(this._onCloseDiscardedClicked, this));
        $closeSubmitted.click(_.bind(this._onCloseSubmittedClicked, this));
        $deletePermanently.click(_.bind(this._onDeleteReviewRequestClicked,
                                        this));

        this.model.fileAttachments.on('add',
                                      this._buildFileAttachmentThumbnail,
                                      this);

        this.model.on('saving', function() {
            this.$draftBannerButtons.prop('disabled', true);
        }, this);

        this.model.on('saved', function() {
            this.$draftBannerButtons.prop('disabled', false);
            this.$draftBanner.show();
        }, this);

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

        /*
         * Set up editors for every registered field.
         */
        _.each(this._fieldEditors, function(fieldOptions) {
            var $el = $('#' + fieldOptions.elementID);

            if (fieldOptions.elementOptional && $el.length === 0) {
                return;
            }

            console.assert($el.length === 1,
                           'There must be one element named "' +
                           fieldOptions.elementID + '"');

            this._buildEditor($el, fieldOptions);

            if (_.has(fieldOptions, 'autocomplete')) {
                this._buildAutoComplete($el, fieldOptions.autocomplete);
            }

            draft.on('change:' + fieldOptions.fieldName,
                     _.bind(this._formatField, this, fieldOptions));
        }, this);

        /* Linkify any text in the description and testing done. */
        _.each($("#description, #testing_done"), function(el) {
            var $el = $(el);

            $el.html(this.linkifyText($el.text()));
        }, this);

        this.model.on('change:editable', this._onEditableChanged, this);
        this._onEditableChanged();

        return this;
    },

    /*
     * Converts an array of items to a list of hyperlinks.
     *
     * By default, this will use the item as the URL and as the hyperlink text.
     * By overriding urlFunc and textFunc, the URL and text can be customized.
     */
    urlizeList: function(list, urlFunc, textFunc, postProcessFunc) {
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
     * This is a wrapper around RB.linkifyText that handles passing in
     * the bug tracker.
     */
    linkifyText: function(text) {
        var reviewRequest = this.model.get('reviewRequest');

        return RB.linkifyText(text || '', reviewRequest.get('bugTrackerURL'));
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
    _buildFileAttachmentThumbnail: function(fileAttachment, collection,
                                            options) {
        var fileAttachmentComments = this.model.get('fileAttachmentComments'),
            $thumbnail = options ? options.$el : undefined,
            view = new RB.FileAttachmentThumbnail({
                el: $thumbnail,
                model: fileAttachment,
                comments: fileAttachmentComments[fileAttachment.id],
                renderThumbnail: ($thumbnail === undefined),
                reviewRequest: this.model.get('reviewRequest')
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
            RB.showReviewBanner();
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
            fileAttachment = reviewRequest.createFileAttachment({
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
        var self = this,
            model = this.model,
            el = $el[0],
            id = el.id;

        $el
            .inlineEditor({
                cls: id + '-editor',
                editIconPath: STATIC_URLS['rb/images/edit.png'],
                multiline: el.tagName === 'PRE',
                showButtons: !$el.hasClass('screenshot-editable'),
                startOpen: fieldOptions.startOpen,
                useEditIconOnly: fieldOptions.useEditIconOnly,
                showRequiredFlag: $el.hasClass('required')
            })
            .on({
                beginEdit: function() {
                    model.incr('editCount');
                },
                cancel: function() {
                    model.decr('editCount');
                },
                complete: function(e, value) {
                    model.decr('editCount');
                    self._setDraftField(value, fieldOptions);
                }
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
                        s += ' <span>(' + data[options.descKey] + ')</span>';
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
                     'api/' + options.fieldName + '/',
                extraParams: options.extraParams
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
                        .text('Press Tab to auto-complete.')
                        .appendTo(resultsPane);
                }
            });
    },

    /*
     * Sets a field in the draft.
     *
     * If we're in the process of publishing, this will check if we have saved
     * all fields before publishing the draft.
     */
    _setDraftField: function(value, fieldOptions) {
        var fieldID = fieldOptions.jsonFieldName,
            model = this.model,
            reviewRequest = model.get('reviewRequest'),
            data = {};

        data[fieldID] = value;

        reviewRequest.draft.save({
            data: data,
            buttons: this.$draftBannerButtons,
            error: _.bind(function(model, xhr) {
                var rsp = xhr.errorPayload,
                    fieldValue = rsp.fields[fieldID],
                    message;

                model.set('publishing', false);

                this._$warning
                    .delay(6000)
                    .fadeOut(400, function() {
                        $(this).hide();
                    });

                /* Wrap each term in quotes or a leading 'and'. */
                _.each(fieldValue, function(key, value) {
                    var size = fieldValue.length;

                    if (key == size - 1 && size > 1) {
                      fieldValue[key] = "and '" + value + "'";
                    } else {
                      fieldValue[key] = "'" + value + "'";
                    }
                });

                message = fieldValue.join(", ");

                if (fieldValue.length === 1) {
                    if (fieldID === "target_groups") {
                        message = "Group " + message + " does not exist.";
                    } else {
                        message = "User " + message + " does not exist.";
                    }
                } else {
                    if (fieldID === "target_groups") {
                        message = "Groups " + message + " do not exist.";
                    } else {
                        message = "Users " + message + " do not exist.";
                    }
                }

                this._$warning
                    .show()
                    .html(message);
            }, this),
            success: _.bind(function() {
                this.$draftBanner.show();

                if (model.get('publishing')) {
                    model.decr('pendingSaveCount');

                    if (model.get('pendingSaveCount') === 0) {
                        this._publishDraft();
                    }
                }
            }, this)
        });
    },

    /*
     * Formats the contents of a field.
     *
     * If there's a registered field formatter for this field, it will
     * be used to display the contents of a field in the draft.
     */
    _formatField: function(fieldOptions) {
        var formatter = fieldOptions.formatter,
            reviewRequest;

        if (_.isFunction(formatter)) {
            reviewRequest = this.model.get('reviewRequest');

            $('#' + fieldOptions.elementID)
                .empty()
                .html(formatter.call(
                    fieldOptions.context || this, this,
                    reviewRequest.draft.get(fieldOptions.fieldName)));
        }
    },

    /*
     * Publishes the draft to the server. This assumes all fields have been
     * saved.
     *
     * Checks all the fields to make sure we have the information we need
     * and then redirects the user to the publish URL.
     */
    _publishDraft: function() {
        if ($.trim($("#target_groups").html()) === "" &&
            $.trim($("#target_people").html()) === "") {
            alert("There must be at least one reviewer or group " +
                  "before this review request can be published.");
        } else if ($.trim($("#summary").html()) === "") {
            alert("The draft must have a summary.");
        } else if ($.trim($("#description").html()) === "") {
            alert("The draft must have a description.");
        } else {
            this.model.get('reviewRequest').draft.publish({
                buttons: this.$draftBannerButtons,
                success: _.bind(this._refreshPage, this)
            });
        }
    },

    /*
     * Handler for when the 'editable' property changes.
     *
     * Enables or disables all inlineEditors.
     */
    _onEditableChanged: function() {
        this.$('.edit, .editable')
            .inlineEditor(this.model.get('editable') ? 'enable' : 'disable');
    },

    /*
     * Handler for when the Publish Draft button is clicked.
     *
     * Begins publishing the review request. If there are any field editors
     * still open, they'll be saved first.
     */
    _onPublishDraftClicked: function() {
        /* Save all the fields if we need to. */
        var fields = this.$(".editable:inlineEditorDirty");

        this.model.set({
            publishing: true,
            pendingSaveCount: fields.length
        });

        if (fields.length === 0) {
            this._publishDraft();
        } else {
            fields.inlineEditor("save");
        }

        return false;
    },

    /*
     * Handler for when the Discard Draft button is clicked.
     *
     * Discards the draft of the review request and relodds the page.
     */
    _onDiscardDraftClicked: function() {
        this.model.get('reviewRequest').draft.destroy({
            buttons: this.$draftBannerButtons,
            success: this._refreshPage
        }, this);

        return false;
    },

    /*
     * Handler for when Close -> Discarded is clicked.
     */
    _onCloseDiscardedClicked: function() {
        this.model.get('reviewRequest').close({
            type: RB.ReviewRequest.CLOSE_DISCARDED,
            buttons: this.$draftBannerButtons,
            success: this._refreshPage
        }, this);

        return false;
    },

    /*
     * Handler for Reopen Review Request.
     */
    _onReopenClicked: function() {
        this.model.get('reviewRequest').reopen({
            buttons: this.$draftBannerButtons,
            success: this._refreshPage
        }, this);

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

        if ($("#draft-banner").is(":visible")) {
            submit = confirm("You have an unpublished draft. If you close " +
                             "this review request, the draft will be " +
                             "discarded. Are you sure you want to close " +
                             "the review request?");
        }

        if (submit) {
            this.model.get('reviewRequest').close({
                type: RB.ReviewRequest.CLOSE_SUBMITTED,
                buttons: this.$draftBannerButtons,
                success: this._refreshPage
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
            .text("This deletion cannot be undone. All diffs and reviews " +
                  "will be deleted as well.")
            .modalBox({
                title: "Are you sure you want to delete this review request?",
                buttons: [
                    $('<input type="button" value="Cancel"/>'),
                    $('<input type="button" value="Delete"/>')
                        .click(_.bind(function() {
                            this.model.get('reviewRequest').destroy({
                                buttons: this.$draftBannerButtons.add(
                                    $("input", dlg.modalBox("buttons"))),
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
        window.location = gReviewRequestPath;
    }
});
