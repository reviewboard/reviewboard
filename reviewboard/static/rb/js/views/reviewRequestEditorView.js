/*
 * Manages the user-visible state of an editable review request.
 *
 * This owns the fields, thumbnails, banners, and general interaction
 * around editing a review request.
 */
RB.ReviewRequestEditorView = Backbone.View.extend({
    /*
     * Renders the editor.
     *
     * This will import all pre-rendered file attachment and screenshot
     * thumbnails, turning them into FileAttachment and Screenshot objects.
     */
    render: function() {
        this._$warning = $('#review-request-warning');
        this._$screenshots = $('#screenshot-thumbnails');
        this._$attachments = $('#file-list');
        this._$attachmentsContainer = $(this._$attachments.parent()[0]);

        this.model.fileAttachments.on('add',
                                      this._buildFileAttachmentThumbnail,
                                      this);

        this.model.on('saving', function() {
            RB.draftBannerButtons.prop('disabled', true);
        }, this);

        this.model.on('saved', function() {
            RB.draftBannerButtons.prop('disabled', false);
            RB.draftBanner.show();
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

        return this;
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
    }
});
