/*
 * Handles all operations and state related to editing review requests.
 *
 * This manages the editing of all fields and objects on a review request,
 * the publishing workflow, and validation.
 */
RB.ReviewRequestEditor = Backbone.Model.extend({
    defaults: {
        commentIssueManager: null,
        editable: false,
        editCount: 0,
        hasDraft: false,
        fileAttachmentComments: {},
        mutableByUser: false,
        pendingSaveCount: 0,
        publishing: false,
        reviewRequest: null,
        statusEditable: false,
        statusMutableByUser: false
    },

    initialize: function() {
        var reviewRequest = this.get('reviewRequest');

        this.fileAttachments = new Backbone.Collection([], {
            model: RB.FileAttachment
        });
        this.fileAttachments.on('add', this._onFileAttachmentOrScreenshotAdded,
                                this);

        this.screenshots = new Backbone.Collection([], {
            model: RB.Screenshot
        });
        this.screenshots.on('add', this._onFileAttachmentOrScreenshotAdded,
                            this);

        reviewRequest.draft.on('saving', function() {
            this.trigger('saving');
        }, this);

        reviewRequest.draft.on('saved', function() {
            this.trigger('saved');
        }, this);

        this.listenTo(reviewRequest, 'change:state', this._computeEditable);
        this._computeEditable();
    },

    /*
     * Creates a file attachment tracked by the editor.
     *
     * This wraps ReviewRequest.createFileAttachment and stores the
     * file attachment in the fileAttachments collection.
     *
     * This should be used instead of ReviewRequest.createFileAttachment
     * for any existing or newly uploaded file attachments.
     */
    createFileAttachment: function(attributes) {
        var draft = this.get('reviewRequest').draft,
            fileAttachment = draft.createFileAttachment(attributes);

        this.fileAttachments.add(fileAttachment);

        return fileAttachment;
    },

    /*
     * Returns a field from the draft.
     *
     * This will look either in the draft's data or in the extraData (for
     * custom fields), returning the value provided either when the page
     * was generated or when it was last edited.
     */
    getDraftField: function(fieldName, options) {
        var reviewRequest = this.get('reviewRequest'),
            draft = reviewRequest.draft;

        if (options.useExtraData) {
            return draft.get('extraData')[options.fieldID];
        } else if (fieldName === 'closeDescription' ||
                   fieldName === 'closeDescriptionRichText') {
            return reviewRequest.get(fieldName);
        } else {
            return draft.get(fieldName);
        }
    },

    /*
     * Sets a field in the draft.
     *
     * If we're in the process of publishing, this will check if we have saved
     * all fields before publishing the draft.
     *
     * Once the field has been saved, two events will be triggered:
     *
     *     * fieldChanged(fieldName, value)
     *     * fieldChanged:<fieldName>(value)
     */
    setDraftField: function(fieldName, value, options, context) {
        var reviewRequest = this.get('reviewRequest'),
            jsonFieldName,
            jsonTextTypeFieldName,
            richText,
            data = {};

        options = options || {};
        richText = !!options.richText;

        if (fieldName === 'closeDescription' && _.has(options, 'closeType')) {
            reviewRequest.close(
                {
                    type: options.closeType,
                    richText: richText,
                    description: value,
                    success: options.success,
                    error: options.error,
                    postData: {
                        force_text_type: 'html',
                        include_text_types: 'raw'
                    }
                },
                context);

            return;
        }

        jsonFieldName = options.jsonFieldName;

        if (options.useExtraData) {
            jsonFieldName = 'extra_data.' + jsonFieldName;
        }

        if (options.allowMarkdown) {
            jsonTextTypeFieldName = options.jsonTextTypeFieldName;

            if (options.useExtraData) {
                jsonTextTypeFieldName = 'extra_data.' + jsonTextTypeFieldName;
            }

            data[jsonTextTypeFieldName] = richText ? 'markdown' : 'plain';

            data.force_text_type = 'html';
            data.include_text_types = 'raw';
        }

        data[jsonFieldName] = value;

        reviewRequest.draft.save({
            data: data,
            error: function(model, xhr) {
                var rsp,
                    fieldValue,
                    fieldValueLen,
                    message = '';

                this.set('publishing', false);

                if (_.isFunction(options.error)) {
                    rsp = xhr.errorPayload;
                    fieldValue = rsp.fields[jsonFieldName];
                    fieldValueLen = fieldValue.length;

                    /* Wrap each term in quotes or a leading 'and'. */
                    _.each(fieldValue, function(value, i) {
                        if (i === fieldValueLen - 1 && fieldValueLen > 1) {
                            if (i > 2) {
                                message += ', ';
                            }

                            message += " and '" + value + "'";
                        } else {
                            if (i > 0) {
                                message += ', ';
                            }

                            message += "'" + value + "'";
                        }
                    });

                    if (fieldName === "targetGroups") {
                        message = interpolate(
                            ngettext('Group %s does not exist.',
                                     'Groups %s do not exist.',
                                     fieldValue.length),
                            [message]);
                    } else if (fieldName === "targetPeople") {
                        message = interpolate(
                            ngettext('User %s does not exist.',
                                     'Users %s do not exist.',
                                     fieldValue.length),
                            [message]);
                    } else if (fieldName === "dependsOn") {
                        message = interpolate(
                            ngettext('Review Request %s does not exist.',
                                     'Review Requests %s do not exist.',
                                     fieldValue.length),
                            [message]);
                    }

                    options.error.call(context, {
                        errorText: message
                    });
                }
            },
            success: function() {
                if (_.isFunction(options.success)) {
                    options.success.call(context);
                }

                this.trigger('fieldChanged:' + fieldName, value);
                this.trigger('fieldChanged', fieldName, value);

                if (this.get('publishing')) {
                    this.decr('pendingSaveCount');

                    if (this.get('pendingSaveCount') === 0) {
                        this.set('publishing', false);
                        this.publishDraft();
                    }
                }
            }
        }, this);
    },

    /*
     * Publishes the draft to the server. This assumes all fields have been
     * saved.
     *
     * If there's an error during saving or validation, the "publishError"
     * event will be triggered with the error message. Otherwise, upon
     * success, the "publish" event will be triggered.
     */
    publishDraft: function() {
        var reviewRequest = this.get('reviewRequest'),
            onError = function(model, xhr) {
                this.trigger('publishError', xhr.errorText);
            };

        reviewRequest.draft.ensureCreated({
            success: function() {
                reviewRequest.draft.publish({
                    success: function() {
                        this.trigger('published');
                    },
                    error: onError
                }, this);
            },
            error: onError
        }, this);
    },

    /*
     * Increments an attribute by 1.
     *
     * The attribute must be an integer.
     */
    incr: function(attr) {
        var value = this.get(attr);
        console.assert(_.isNumber(value));
        this.set(attr, value + 1, {
            validate: true
        });
    },

    /*
     * Decrements an attribute by 1.
     *
     * The attribute must be an integer.
     */
    decr: function(attr) {
        var value = this.get(attr);
        console.assert(_.isNumber(value));
        this.set(attr, value - 1, {
            validate: true
        });
    },

    /*
     * Performs validation on attributes.
     */
    validate: function(attrs) {
        var strings = RB.ReviewRequestEditor.strings;

        if (_.has(attrs, 'editCount') && attrs.editCount < 0) {
            return strings.UNBALANCED_EDIT_COUNT;
        }
    },

    /*
     * Computes the editable state of the review request and open/close states.
     *
     * The review request is editable if the user has edit permissions and it's
     * not closed.
     *
     * The close state and accompanying description is editable if the user
     * has the ability to close the review request and it's currently closed.
     */
    _computeEditable: function() {
        var state = this.get('reviewRequest').get('state'),
            pending = (state === RB.ReviewRequest.PENDING);

        this.set({
            editable: this.get('mutableByUser') && pending,
            statusEditable: this.get('statusMutableByUser') && !pending
        });
    },

    /*
     * Handler for when a FileAttachment or Screenshot is added.
     *
     * Listens for events on the FileAttachment or Screenshot and relays
     * them to the editor.
     */
    _onFileAttachmentOrScreenshotAdded: function(fileAttachment) {
        fileAttachment.on('saving', function() {
            this.trigger('saving');
        }, this);

        fileAttachment.on('saved destroy', function() {
            this.trigger('saved');
        }, this);
    }
}, {
    strings: {
        UNBALANCED_EDIT_COUNT:
            gettext('There is an internal error balancing the edit count')
    }
});
