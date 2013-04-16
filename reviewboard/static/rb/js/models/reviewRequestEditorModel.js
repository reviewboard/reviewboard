/*
 * Handles all operations and state related to editing review requests.
 *
 * This manages the editing of all fields and objects on a review request,
 * the publishing workflow, and validation.
 */
RB.ReviewRequestEditor = Backbone.Model.extend({
    defaults: {
        editCount: 0,
        fileAttachmentComments: {},
        pendingSaveCount: 0,
        publishing: false,
        reviewRequest: null
    },

    initialize: function() {
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
    validate: function(attrs, options) {
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
