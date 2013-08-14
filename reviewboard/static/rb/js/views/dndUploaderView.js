/*
 * Displays an overlay over the page that accepts file drops.
 *
 * The overlay appears as semi-transparent black, and displays a helpful
 * "Drop to Upload" message in the middle.
 *
 * If the user cancels the drop or moves the mouse out of the page, the
 * overlay will fade away.
 */
var DnDDropOverlayView = Backbone.View.extend({
    className: 'dnd-overlay',

    events: {
        'dragleave': '_onDragLeave',
        'drop': '_onDrop',
        'dragover': '_onDragOver',
        'mouseenter': '_onMouseEnter'
    },

    render: function() {
        var height = $(window).height();

        this.$el
            .width($(window).width())
            .height(height)
            .css('line-height', height + 'px')
            .text(gettext('Drop to Upload'));

        return this;
    },

    /*
     * Closes the overlay.
     *
     * The overlay will fade out, and once it's gone, it'll emit
     * "closed" and remove itself from the page.
     */
    close: function() {
        this.$el.fadeOut(_.bind(function() {
            this.trigger('closed');
            this.remove();
        }, this));
    },

    /*
     * Handles drop events on the overlay.
     *
     * If there are any files, it will emit filesDropped.
     *
     * The overlay will close after any drops on the page.
     */
    _onDrop: function(event) {
        var dt = event.originalEvent.dataTransfer,
            files = dt && dt.files;

        /* Do these early in case we hit some error. */
        event.stopPropagation();
        event.preventDefault();

        if (files) {
            this.trigger('filesDropped', files);
        }

        this.close();
    },

    /*
     * Handles dragover events on the overlay.
     *
     * If there's files being dragged, the drop effect (usually represented
     * by a mouse cursor) will be set to indicate a copy of the files.
     */
    _onDragOver: function(event) {
        var dt = event.originalEvent.dataTransfer;

        if (dt) {
            dt.dropEffect = "copy";
        }

        return false;
    },

    /*
     * Handles dragleave events on the overlay.
     *
     * If there were files previously being dragged over the overlay,
     * the drop effect will be reset.
     *
     * The overlay is always closed on a dragleave.
     */
    _onDragLeave: function(event) {
        var dt = event.originalEvent.dataTransfer;

        if (dt) {
            dt.dropEffect = "none";
        }

        this.close();

        return false;
    },

    /*
     * Handles mouseenter events on the overlay.
     *
     * If we get a mouse enter, then the user has moved the mouse over
     * the DnD overlay without there being any drag-and-drop going on.
     * This is likely due to the broken Firefox 4+ behavior where
     * dragleave events when leaving windows aren't firing.
     */
    _onMouseEnter: function() {
        this.close();

        return false;
    }
});


/*
 * Handles drag-and-drop file uploads for a review request.
 *
 * This makes it possible to drag files from a file manager and drop them
 * into Review Board. This requires browser support for HTML 5 file
 * drag-and-drop, which is available in most modern browsers.
 *
 * The moment the DnDUploader is created, it will begin listening for
 * DnD-related events on the document.
 */
RB.DnDUploader = Backbone.View.extend({
    initialize: function() {
        this._dropOverlay = null;

        $(document.body).on('dragenter', _.bind(this._onDragEnter, this));
    },

    /*
     * Handles dragenter events on the document.
     *
     * An overlay will be displayed to give the user a place to drop
     * the files onto. The overlay will report any files dropped, if
     * any.
     */
    _onDragEnter: function(event) {
        if (!this._dropOverlay &&
            _.indexOf(event.originalEvent.dataTransfer.types, 'Files') !== -1) {

            this._dropOverlay = new DnDDropOverlayView();
            this._dropOverlay.render().$el.appendTo(document.body);
            this._dropOverlay.on('filesDropped', function(files) {
                _.each(files, this._uploadFile, this);
            }, this);
            this._dropOverlay.on('closed', function() {
                this._dropOverlay = null;
            }, this);
        }
    },

    /*
     * Uploads a dropped file as a file attachment.
     *
     * A temporary file attachment placeholder will appear while the
     * file attachment uploads. After the upload has finished, it will
     * be replaced with the thumbnail depicting the file attachment.
     */
    _uploadFile: function(file) {
        /* Create a temporary file listing. */
        var editor = this.options.reviewRequestEditor,
            fileAttachment = editor.createFileAttachment();

        fileAttachment.set('file', file);
        fileAttachment.save();
    }
});
