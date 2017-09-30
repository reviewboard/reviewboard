(function() {


/**
 * A model for creating drag and drop targets.
 *
 * Registering a RB.DnDDropTarget with the RB.DnDUploader will create an
 * overlay on top of the target when files are dragged over the page. This
 * overlay will accept dropped files and run the dropAction for each file
 * dropped on it.
 *
 * Model Attributes:
 *     $target (jQuery):
 *         The target element to allow file drops on.
 *
 *     callback (function):
 *         The function to call when a file is dropped.
 *
 *     dropText (string):
 *         The string to show in the overlay.
 */
const DnDDropTarget = Backbone.Model.extend({
    defaults() {
        return {
            $target: $(window),
            callback: function() {},
            dropText: gettext('Drop to upload')
        };
    }
});


/**
 * Displays an overlay over an element that accepts file drops.
 *
 * The overlay appears as semi-transparent black with the dropText message in
 * the center.
 *
 * If the user cancels the drop or moves the mouse out of the page, the
 * overlay will fade away.
 */
const DnDDropOverlayView = Backbone.View.extend({
    className: 'dnd-overlay',

    events: {
        'dragenter': '_onDragEnter',
        'dragover': '_onDragOver',
        'dragleave': '_onDragLeave',
        'drop': '_onDrop'
    },

    /**
     * Render the view.
     *
     * Returns:
     *     DnDDropOverlayView:
     *     This object, for chaining.
     */
    render() {
        this.$el.text(this.model.get('dropText'));

        return this;
    },

    /**
     * Show the overlay.
     */
    show() {
        const $target = this.model.get('$target');
        $target.addClass('dnd-overlay-visible');

        /*
         * Adding the class to the target may change its visibility or size.
         * Let that clear before trying to position/size the overlay.
         */
        _.defer(() => {
            const offset = $target.offset();
            const width = $target.outerWidth() + 'px';
            const height = $target.outerHeight() + 'px';

            this.$el
                .css({
                    width: width,
                    height: height,
                    'line-height': height,
                    left: offset.left + 'px',
                    top: offset.top + 'px'
                })
                .show();
        });
    },

    /**
     * Hide the overlay.
     */
    hide() {
        this.model.get('$target').removeClass('dnd-overlay-visible');
        this.$el.hide();
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
     * This will call the appropriate callback for all dropped files.
     *
     * Args:
     *     e (DragEvent):
     *         The event that triggered the callback.
     */
    _onDrop(e) {
        e.stopPropagation();
        e.preventDefault();

        const dt = e.originalEvent.dataTransfer;
        const files = dt && dt.files;

        if (files) {
            const callback = this.model.get('callback');

            for (let file of Array.from(files)) {
                callback(file);
            }
        }

        this.trigger('closing');
    },

    /**
     * Handle dragenter events on the overlay.
     *
     * If there's files being dragged, the drop effect (usually represented
     * by a mouse cursor) will be set to indicate a copy of the files.
     *
     * Args:
     *     e (DragEvent):
     *         The event that triggered the callback.
     */
    _onDragEnter(e) {
        e.preventDefault();

        const dt = e.originalEvent.dataTransfer;

        if (dt) {
            dt.dropEffect = 'copy';
            this.$el.addClass('dnd-overlay-highlight');
        }
    },

    /**
     * Handle dragover events on the overlay.
     *
     * This merely prevents the default action, which indicates to the
     * underlying API that this element can be dropped on.
     *
     * Args:
     *     e (DragEvent):
     *         The event which triggered the callback.
     */
    _onDragOver(e) {
        e.preventDefault();
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
     *     e (DragEvent):
     *         The event that triggered the callback.
     */
    _onDragLeave(e) {
        e.preventDefault();

        const dt = e.originalEvent.dataTransfer;

        if (dt) {
            dt.dropEffect = 'none';
            this.$el.removeClass('dnd-overlay-highlight');
        }
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
 * DnD-related events on the window.
 */
RB.DnDUploader = Backbone.View.extend({
    /**
     * Initialize the view.
     */
    initialize() {
        this._dropTargets = new Backbone.Collection({
            model: DnDDropTarget
        });
        this._dropOverlays = [];
        this._hideOverlayTimeout = null;
        this._overlaysVisible = false;
        this._overlaysHiding = false;

        _.bindAll(this, '_showOverlays', '_hideOverlays');

        $(window)
            .on('dragstart dragenter dragover', this._showOverlays)
            .on('dragend dragleave', this._hideOverlays);
    },

    /**
     * Register a new drop target.
     *
     * Args:
     *     $target (jQuery):
     *         The target element for drops.
     *
     *     dropText (string):
     *         The text to show on the overlay.
     *
     *     callback (function):
     *         The function to call when a file is dropped. This takes a single
     *         file argument, and will be called for each file that is dropped
     *         on the target.
     */
    registerDropTarget($target, dropText, callback) {
        if (this._dropTargets.findWhere({ $target }) === undefined) {
            const target = new DnDDropTarget({
                $target,
                dropText,
                callback
            });
            this._dropTargets.add(target);

            const overlay = new DnDDropOverlayView({
                model: target
            });

            overlay.render().$el
                .hide()
                .appendTo(document.body);
            this.listenTo(overlay, 'closing', this._hideOverlays);

            this._dropOverlays.push(overlay);
        } else {
            console.error('Drop target was already registered!', $target);
        }
    },

    /**
     * Unregister an existing drop target.
     *
     * Args:
     *     $target (jQuery):
     *         The target element for drops.
     */
    unregisterDropTarget($target) {
        const target = this._dropTargets.findWhere({ $target: $target });
        const overlayIx = this._dropOverlays.findIndex(
            overlay => (overlay.model === target));

        if (overlayIx !== -1) {
            this._dropOverlays[overlayIx].remove();
            this._dropOverlays.splice(overlayIx, 1);
        }

        if (target !== undefined) {
            this._dropTargets.remove(target);
        }
    },

    /**
     * Show the drop overlays.
     *
     * An overlay will be displayed over all the registered drop targets to
     * give the user a place to drop the files onto. The overlay will report
     * any files dropped.
     *
     * Args:
     *     e (DragEvent):
     *         The event that triggered the callback.
     */
    _showOverlays(e) {
        if (e.originalEvent.dataTransfer !== undefined &&
            Array.from(e.originalEvent.dataTransfer.types).includes('Files')) {
            this._overlaysHiding = false;

            if (!this._overlaysVisible) {
                this._overlaysVisible = true;
                this._dropOverlays.forEach(overlay => overlay.show());
            }
        }
    },

    /**
     * Hide the drop overlays.
     */
    _hideOverlays() {
        /*
         * This will get called many times because the event bubbles up from
         * all the children of the document. We only want to hide the overlays
         * when the drag exits the window.
         *
         * In order to make this work reliably, we only hide the overlays after
         * a timeout (to make sure there's not a dragenter event coming
         * immediately after this).
         */
        if (this._hideOverlayTimeout) {
            clearTimeout(this._hideOverlayTimeout);
        }

        this._overlaysHiding = true;
        this._hideOverlayTimeout = setTimeout(() => {
            if (this._overlaysHiding) {
                this._overlaysVisible = false;
                this._dropOverlays.forEach(overlay => overlay.hide());
            }
        }, 200);
    }
}, {
    instance: null,

    /**
     * Create the DnDUploader instance.
     *
     * Returns:
     *     RB.DnDUploader:
     *     The new instance.
     */
    create() {
        console.assert(RB.DnDUploader.instance === null,
                       'DnDUploader.create may only be called once');

        RB.DnDUploader.instance = new RB.DnDUploader();
        return RB.DnDUploader.instance;
    }
});


})();
