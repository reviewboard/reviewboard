import {
    BaseModel,
    BaseView,
    Collection,
    EventsHash,
    spina,
} from '@beanbag/spina';


/**
 * A model for creating drag and drop targets.
 *
 * Registering a DnDDropTarget with the DnDUploader will create an
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
@spina
class DnDDropTarget extends BaseModel {
    defaults() {
        return {
            $target: $(window),
            callback: function() {},
            dropText: _`Drop to upload`,
        };
    }
}


/**
 * Displays an overlay over an element that accepts file drops.
 *
 * The overlay appears as semi-transparent black with the dropText message in
 * the center.
 *
 * If the user cancels the drop or moves the mouse out of the page, the
 * overlay will fade away.
 */
@spina
class DnDDropOverlayView extends BaseView<DnDDropTarget> {
    static className = 'dnd-overlay';

    static events: EventsHash = {
        'dragenter': '_onDragEnter',
        'dragleave': '_onDragLeave',
        'dragover': '_onDragOver',
        'drop': '_onDrop',
    };

    /**
     * Render the view.
     */
    onInitialRender() {
        this.$el.text(this.model.get('dropText'));
    }

    /**
     * Show the overlay.
     *
     * Returns:
     *     DnDDropOverlayView:
     *     This object, for chaining.
     */
    show(): this {
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
                    'height': height,
                    'left': offset.left + 'px',
                    'line-height': height,
                    'top': offset.top + 'px',
                    'width': width,
                })
                .show();
        });

        return this;
    }

    /**
     * Hide the overlay.
     *
     * Returns:
     *     DnDDropOverlayView:
     *     This object, for chaining.
     */
    hide(): this {
        this.model.get('$target').removeClass('dnd-overlay-visible');
        this.$el.hide();

        return this;
    }

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
    }

    /**
     * Handle drop events on the overlay.
     *
     * This will call the appropriate callback for all dropped files.
     *
     * Args:
     *     e (DragEvent):
     *         The event that triggered the callback.
     */
    private _onDrop(e: JQuery.DragEvent) {
        e.stopPropagation();
        e.preventDefault();

        const dt = e.originalEvent.dataTransfer;
        const files = dt && dt.files;

        if (files) {
            const callback = this.model.get('callback');

            for (const file of Array.from(files)) {
                callback(file);
            }
        }

        this.trigger('closing');
    }

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
    private _onDragEnter(e: JQuery.DragEvent) {
        e.preventDefault();

        const dt = e.originalEvent.dataTransfer;

        if (dt) {
            dt.dropEffect = 'copy';
            this.$el.addClass('dnd-overlay-highlight');
        }
    }

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
    private _onDragOver(e: JQuery.DragEvent) {
        e.preventDefault();
    }

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
    private _onDragLeave(e: JQuery.DragEvent) {
        e.preventDefault();

        const dt = e.originalEvent.dataTransfer;

        if (dt) {
            dt.dropEffect = 'none';
            this.$el.removeClass('dnd-overlay-highlight');
        }
    }
}


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
@spina({
    prototypeAttrs: ['instance'],
})
export class DnDUploader extends BaseView {
    static instance: DnDUploader = null;

    /**
     * Create the DnDUploader instance.
     *
     * Returns:
     *     DnDUploader:
     *     The new instance.
     */
    static create(): DnDUploader {
        console.assert(this.instance === null,
                       'DnDUploader.create may only be called once');

        this.instance = new this();

        return this.instance;
    }

    /**********************
     * Instance variables *
     **********************/

    /**
     * The set of drop targets for the page.
     */
    #dropTargets: Collection<DnDDropTarget>;

    /**
     * The overlay views.
     */
    #dropOverlays: DnDDropOverlayView[] = [];

    /**
     * The timeout identifier for hiding the overlays.
     */
    #hideOverlayTimeout: number = null;

    /**
     * Whether the drop overlays are visible.
     */
    #overlaysVisible = false;

    /**
     * Whether the drop overlays are in the process of hiding.
     */
    #overlaysHiding = false;

    /**
     * Initialize the view.
     */
    initialize() {
        this.#dropTargets = new Collection<DnDDropTarget>();

        _.bindAll(this, '_showOverlays', '_hideOverlays');

        $(window)
            .on('dragstart dragenter dragover', this._showOverlays)
            .on('dragend dragleave', this._hideOverlays);
    }

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
        if (this.#dropTargets.findWhere({ $target }) === undefined) {
            const target = new DnDDropTarget({
                $target,
                callback,
                dropText,
            });
            this.#dropTargets.add(target);

            const overlay = new DnDDropOverlayView({
                model: target,
            });

            overlay.render().$el
                .hide()
                .appendTo(document.body);
            this.listenTo(overlay, 'closing', this._hideOverlays);

            this.#dropOverlays.push(overlay);
        } else {
            console.error('Drop target was already registered!', $target);
        }
    }

    /**
     * Unregister an existing drop target.
     *
     * Args:
     *     $target (jQuery):
     *         The target element for drops.
     */
    unregisterDropTarget($target) {
        const target = this.#dropTargets.findWhere({ $target: $target });
        const overlayIx = this.#dropOverlays.findIndex(
            overlay => (overlay.model === target));

        if (overlayIx !== -1) {
            this.#dropOverlays[overlayIx].remove();
            this.#dropOverlays.splice(overlayIx, 1);
        }

        if (target !== undefined) {
            this.#dropTargets.remove(target);
        }
    }

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
    private _showOverlays(e) {
        if (e.originalEvent.dataTransfer !== undefined &&
            Array.from(e.originalEvent.dataTransfer.types).includes('Files')) {
            this.#overlaysHiding = false;

            if (!this.#overlaysVisible) {
                this.#overlaysVisible = true;
                this.#dropOverlays.forEach(overlay => overlay.show());
            }
        }
    }

    /**
     * Hide the drop overlays.
     */
    private _hideOverlays() {
        /*
         * This will get called many times because the event bubbles up from
         * all the children of the document. We only want to hide the overlays
         * when the drag exits the window.
         *
         * In order to make this work reliably, we only hide the overlays after
         * a timeout (to make sure there's not a dragenter event coming
         * immediately after this).
         */
        if (this.#hideOverlayTimeout) {
            clearTimeout(this.#hideOverlayTimeout);
        }

        this.#overlaysHiding = true;
        this.#hideOverlayTimeout = setTimeout(() => {
            if (this.#overlaysHiding) {
                this.#overlaysVisible = false;
                this.#dropOverlays.forEach(overlay => overlay.hide());
            }
        }, 200);
    }
}
