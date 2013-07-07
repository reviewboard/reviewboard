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
        pendingSaveCount: 0,
        publishing: false,
        reviewRequest: null
    },

    _jsonFieldMap: {
        bugsClosed: 'bugs_closed',
        changeDescription: 'changedescription',
        dependsOn: 'depends_on',
        targetGroups: 'target_groups',
        targetPeople: 'target_people',
        testingDone: 'testing_done'
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
        var reviewRequest = this.get('reviewRequest'),
            fileAttachment = reviewRequest.createFileAttachment(attributes);

        this.fileAttachments.add(fileAttachment);

        return fileAttachment;
    },

    /*
     * Sets a field in the draft.
     *
     * If we're in the process of publishing, this will check if we have saved
     * all fields before publishing the draft.
     */
    setDraftField: function(fieldName, value, options, context) {
        var reviewRequest = this.get('reviewRequest'),
            jsonFieldName,
            data = {};

        options = options || {};

        if (fieldName === 'changeDescription' && _.has(options, 'closeType')) {
            reviewRequest.close({
                type: options.closeType,
                description: value
            });

            return;
        }

        jsonFieldName = this._jsonFieldMap[fieldName] || fieldName;
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

                    if (fieldValue.length === 1) {
                        if (fieldName === "targetGroups") {
                            message = "Group " + message + " does not exist.";
                        } else if (fieldName === "targetPeople") {
                            message = "User " + message + " does not exist.";
                        } else if (fieldName === "dependsOn") {
                            message = "Review request " + message +
                                      " does not exist.";
                        }
                    } else {
                        if (fieldName === "targetGroups") {
                            message = "Groups " + message + " do not exist.";
                        } else if (fieldName === "targetPeople") {
                            message = "Users " + message + " do not exist.";
                        } else if (fieldName === "dependsOn") {
                            message = "Review requests " + message +
                                      " do not exist.";
                        }
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
        var reviewRequest = this.get('reviewRequest');

        reviewRequest.draft.publish({
            success: function() {
                this.trigger('published');
            },
            error: function(error) {
                this.trigger('publishError', error.errorText);
            }
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
            'There is an internal error balancing the edit count'
    }
});
