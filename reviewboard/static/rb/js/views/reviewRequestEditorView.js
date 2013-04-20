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

    /*
     * Renders the editor.
     *
     * This will import all pre-rendered file attachment and screenshot
     * thumbnails, turning them into FileAttachment and Screenshot objects.
     */
    render: function() {
        var $closeDiscarded = this.$('#discard-review-request-link'),
            $closeSubmitted = this.$('#link-review-request-close-submitted'),
            $deletePermanently = this.$('#delete-review-request-link');

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

        this.model.on('change:editable', this._onEditableChanged, this);
        this._onEditableChanged();

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
    },

    /*
     * Handler for when the 'editable' property changes.
     *
     * Enables or disables all inlineEditors.
     */
    _onEditableChanged: function() {
        this.$('.edit')
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
            RB.publishDraft();
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
            buttons: RB.draftBannerButtons,
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
            buttons: RB.draftBannerButtons,
            success: this._refreshPage
        }, this);

        return false;
    },

    /*
     * Handler for Reopen Review Request.
     */
    _onReopenClicked: function() {
        this.model.get('reviewRequest').reopen({
            buttons: RB.draftBannerButtons,
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
                buttons: RB.draftBannerButtons,
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
                                buttons: RB.draftBannerButtons.add(
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
