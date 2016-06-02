{


/**
 * Displays an overlay over the page that accepts file drops.
 *
 * The overlay appears as semi-transparent black, and displays a helpful
 * "Drop to Upload" message in the middle.
 *
 * If the user cancels the drop or moves the mouse out of the page, the
 * overlay will fade away.
 */
const DnDDropOverlayView = Backbone.View.extend({
    className: 'dnd-overlay',

    events: {
        'dragleave': '_onDragLeave',
        'drop': '_onDrop',
        'dragover': '_onDragOver',
        'mouseenter': '_onMouseEnter'
    },

    /**
     * Render the view.
     *
     * Returns:
     *     DnDDropOverlayView:
     *     This object, for chaining.
     */
    render() {
        const $window = $(window);
        const height = $window.height();
        const width = $window.width();

        this.$el
            .width(width)
            .height(height)
            .css('line-height', height + 'px')
            .text(gettext('Drop to Upload'));

        return this;
    },

    /**
     * Close the overlay.
     *
     * The overlay will fade out, and once it's gone, it will emit the "closed"
     * event and remove itself from the page.
     */
    close() {
        this.$el.fadeOut(() => {
            this.trigger('closed');
            this.remove();
        });
    },

    /**
     * Handle drop events on the overlay.
     *
     * If there are any files, it will emit the "filesDropped" event. Once that
     * is done, the overlay will close.
     *
     * Args:
     *     e (Event):
     *         The event that triggered the callback.
     */
    _onDrop(e) {
        e.stopPropagation();
        e.preventDefault();

        const dt = e.originalEvent.dataTransfer;
        const files = dt && dt.files;

        if (files) {
            this.trigger('filesDropped', files);
        }

        this.close();
    },

    /**
     * Handle dragover events on the overlay.
     *
     * If there's files being dragged, the drop effect (usually represented
     * by a mouse cursor) will be set to indicate a copy of the files.
     *
     * Args:
     *     e (Event):
     *         The event that triggered the callback.
     */
    _onDragOver(e) {
        e.stopPropagation();
        e.preventDefault();

        const dt = e.originalEvent.dataTransfer;

        if (dt) {
            dt.dropEffect = 'copy';
        }
    },

    /**
     * Handle dragleave events on the overlay.
     *
     * If there were files previously being dragged over the overlay,
     * the drop effect will be reset.
     *
     * The overlay is always closed on a dragleave.
     *
     * Args:
     *     e (Event):
     *         The event that triggered the callback.
     */
    _onDragLeave(e) {
        e.stopPropagation();
        e.preventDefault();

        const dt = e.originalEvent.dataTransfer;

        if (dt) {
            dt.dropEffect = "none";
        }

        this.close();
    },

    /**
     * Handles mouseenter events on the overlay.
     *
     * If we get a mouse enter, then the user has moved the mouse over
     * the DnD overlay without there being any drag-and-drop going on.
     * This is likely due to the broken Firefox 4+ behavior where
     * dragleave events when leaving windows aren't firing.
     *
     * Args:
     *     e (Event):
     *         The event that triggered the callback.
     */
    _onMouseEnter(e) {
        e.stopPropagation();
        e.preventDefault();

        this.close();
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
    /**
     * Initialize the view.
     */
    initialize() {
        this._dropOverlay = null;

        $(document.body).on('dragenter', this._onDragEnter.bind(this));
    },

    /**
     * Handle dragenter events on the document.
     *
     * An overlay will be displayed to give the user a place to drop
     * the files onto. The overlay will report any files dropped, if
     * any.
     *
     * Args:
     *     e (Event):
     *         The event that triggered the callback.
     */
    _onDragEnter(e) {
        if (!this._dropOverlay &&
            Array.from(e.originalEvent.dataTransfer.types).includes('Files')) {
            this._dropOverlay = new DnDDropOverlayView();
            this._dropOverlay.render().$el.appendTo(document.body);
            this.listenTo(this._dropOverlay, 'closed',
                          () => {
                              this._dropOverlay = null;
                          });
            this.listenTo(
                this._dropOverlay,
                'filesDropped',
                files => {
                    for (let file of Array.from(files)) {
                        this._uploadFile(file);
                    }
                });
        }
    },

    /**
     * Upload a dropped file as a file attachment.
     *
     * A temporary file attachment placeholder will appear while the
     * file attachment uploads. After the upload has finished, it will
     * be replaced with the thumbnail depicting the file attachment.
     *
     * Args:
     *     file (file):
     *         The file to upload.
     */
    _uploadFile(file) {
        const editor = this.options.reviewRequestEditor;
        const fileAttachment = editor.createFileAttachment();

        fileAttachment.set('file', file);
        fileAttachment.save();
    }
});


}
