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
            selector: '#bugs_closed',
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
            selector: '#draft-banner #changedescription',
            jsonFieldName: 'changedescription',
            elementOptional: true,
            startOpen: true
        },
        {
            fieldName: 'changeDescription',
            selector: '#submitted-banner #changedescription',
            jsonFieldName: 'changedescription',
            elementOptional: true,
            closeType: RB.ReviewRequest.CLOSE_SUBMITTED
        },
        {
            fieldName: 'changeDescription',
            selector: '#discard-banner #changedescription',
            jsonFieldName: 'changedescription',
            elementOptional: true,
            closeType: RB.ReviewRequest.CLOSE_DISCARDED
        },
        {
            fieldName: 'dependsOn',
            selector: '#depends_on',
            jsonFieldName: 'depends_on',
            useEditIconOnly: true,
            formatter: function(view, data) {
                return view.urlizeList(
                    data,
                    function(item) { return item.url; },
                    function(item) { return item.id; }
                );
            }
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
            selector: '#target_groups',
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
            selector: '#target_people',
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
            selector: '#testing_done',
            jsonFieldName: 'testing_done',
            formatter: function(view, data) {
                return view.linkifyText(data);
            }
        }
    ],

    initialize: function() {
        this._fieldEditors = [];

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

        this._fieldEditors.push(_.extend({
            selector: '#' + options.fieldName,
            elementOptional: false,
            formatter: null,
            jsonFieldName: options.fieldName,
            startOpen: false,
            useEditIconOnly: false
        }, options));
    },

    /*
     * Renders the editor.
     *
     * This will import all pre-rendered file attachment and screenshot
     * thumbnails, turning them into FileAttachment and Screenshot objects.
     */
    render: function() {
        var draft = this.model.get('reviewRequest').draft;

        this.$draftBanner = $('#draft-banner');
        this.$draftBannerButtons = this.$draftBanner.find('input');

        this._$box = this.$('.review-request');
        this._$warning = $('#review-request-warning');
        this._$screenshots = $('#screenshot-thumbnails');
        this._$attachments = $('#file-list');
        this._$attachmentsContainer = $(this._$attachments.parent()[0]);

        this.dndUploader = new RB.DnDUploader({
            reviewRequestEditor: this.model
        });

        this._setupActions();

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

        this.model.on('publishError', function(errorText) {
            alert(errorText);
        });

        this.model.on('published', this._refreshPage, this);

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
            var $el = this.$(fieldOptions.selector);

            if ($el.length === 0) {
                return;
            }

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

        /*
         * Warn the user if they try to navigate away with unsaved comments.
         */
        window.onbeforeunload = _.bind(function(evt) {
            if (this.model.get('editable') &&
                this.model.get('editCount') > 0) {
                /*
                 * On IE, the text must be set in evt.returnValue.
                 *
                 * On Firefox, it must be returned as a string.
                 *
                 * On Chrome, it must be returned as a string, but you
                 * can't set it on evt.returnValue (it just ignores it).
                 */
                var msg = "You have unsaved changes that will " +
                          "be lost if you navigate away from " +
                          "this page.";
                evt = evt || window.event;

                evt.returnValue = msg;
                return msg;
            }
        }, this);

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
        var model = this.model,
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
                complete: _.bind(function(e, value) {
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
                                this.$draftBanner.show();
                            }
                        }, fieldOptions),
                        this);
                }, this)
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
                     'api/' + (options.resourceName || options.fieldName) + '/',
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
     * Formats the contents of a field.
     *
     * If there's a registered field formatter for this field, it will
     * be used to display the contents of a field in the draft.
     */
    _formatField: function(fieldOptions) {
        var formatter = fieldOptions.formatter,
            $el = this.$(fieldOptions.selector),
            reviewRequest = this.model.get('reviewRequest'),
            value = reviewRequest.draft.get(fieldOptions.fieldName);

        if (_.isFunction(formatter)) {
            $el.html(formatter.call(fieldOptions.context || this, this, value));
        } else {
            $el.text(value);
        }
    },

    /*
     * Handler for when the 'editable' property changes.
     *
     * Enables or disables all inlineEditors.
     */
    _onEditableChanged: function() {
        this._$box.find('.edit, .editable')
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
            this.model.publishDraft();
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
