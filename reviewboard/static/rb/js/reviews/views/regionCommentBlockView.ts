/**
 * Provides a visual region over an image or other document showing comments.
 */

import { EventsHash, spina } from '@beanbag/spina';

import { RegionCommentBlock } from '../models/regionCommentBlockModel';
import { AbstractCommentBlockView } from './abstractCommentBlockView';
import { CommentDialogView } from './commentDialogView';


/** A structure to hold the region size for a selection. */
type SelectionRegion = {
    height: number;
    width: number;
};

/** Type for the callback when a drag occurs.*/
type DragCallback = (pageX: number, pageY: number) => void;

/** Type for the function that returns the current selection region. */
type SelectionRegionSizeFunc = () => SelectionRegion;


/**
 * Stored state when moving a region comment.
 */
interface MoveState {
    dragCallback: DragCallback;
    hasMoved: boolean;
    initialBounds: {
        height?: number;
        left?: number;
        top?: number;
        width?: number;
    };
    initialCursor: {
        left?: number;
        top?: number;
    };
}


/**
 * Provides a visual region over an image or other document showing comments.
 *
 * This will show a selection rectangle over part of an image or other
 * content indicating there are comments there. It will also show the
 * number of comments, along with a tooltip showing comment summaries.
 *
 * This is meant to be used with a RegionCommentBlock model.
 */
@spina
export class RegionCommentBlockView<
    TModel extends RegionCommentBlock = RegionCommentBlock,
    TElement extends Element = HTMLElement,
    TExtraViewOptions = unknown
> extends AbstractCommentBlockView<TModel, TElement, TExtraViewOptions> {
    static className = 'selection';

    static events: EventsHash = _.defaults({
        'click': '_onClicked',
        'mousedown': '_onMouseDown',
    }, super.events);

    static modelEvents: EventsHash = _.defaults({
        'change:count': '_updateCount',
        'change:x change:y change:width change:height': '_updateBounds',
    }, super.modelEvents);

    /**********************
     * Instance variables *
     **********************/

    /** The selection flag. */
    #$flag: JQuery = null;

    /** The JQuery-wrapped window object. */
    #$window: JQuery<Window> = $(window);

    /** The icon for resizing the comment region. */
    #$resizeIcon: JQuery = null;

    /** The scale to adjust the stored region. */
    #scale = 1.0;

    /** The stored state when moving a region comment. */
    #moveState: MoveState = {
        dragCallback: _.noop,
        hasMoved: false,
        initialBounds: {},
        initialCursor: {},
    };

    /** The function to get the selection region. */
    private _selectionRegionSizeFunc: SelectionRegionSizeFunc;

    /**
     * Initialize RegionCommentBlockView.
     */
    initialize() {
        _.bindAll(this, '_onDrag', '_onWindowMouseUp');
    }

    /**
     * Un-listen to events.
     *
     * Returns:
     *     RegionCommentBlockView:
     *     This object, for chaining.
     */
    undelegateEvents(): this {
        super.undelegateEvents();

        this.#$window.off(`mousemove.${this.cid}`);

        return this;
    }

    /**
     * Set the selection region size function.
     *
     * This function is meant to return the maximum size of the selection
     * region for the given comment.
     *
     * Args:
     *     func (function):
     *         A function which will return a size object.
     */
    setSelectionRegionSizeFunc(func: SelectionRegionSizeFunc) {
        this._selectionRegionSizeFunc = func;
    }

    /**
     * Return the selection region size.
     *
     * Returns:
     *     object:
     *     An object with ``x``, ``y``, ``width``, and ``height`` fields, in
     *     pixels.
     */
    getSelectionRegionSize(): SelectionRegion {
        return _.result(this, '_selectionRegionSizeFunc');
    }

    /**
     * Initiate a drag operation.
     *
     * Args:
     *     left (number):
     *         The initial left position of the cursor.
     *
     *     top (number):
     *         The initial top position of the cursor.
     *
     *     callback (function):
     *         A callback function to call once the drag is finished.
     */
    _startDragging(
        left: number,
        top: number,
        callback: DragCallback,
    ) {
        /*
         * ``hasMoved`` is used to distinguish dragging from clicking.
         * ``initialCursor`` and ``initialBounds`` are used to calculate the
         * new position and size while dragging.
         */
        const moveState = this.#moveState;
        moveState.hasMoved = false;
        moveState.initialCursor.left = left;
        moveState.initialCursor.top = top;
        moveState.initialBounds.left = this.$el.position().left;
        moveState.initialBounds.top = this.$el.position().top;
        moveState.initialBounds.width = this.$el.width();
        moveState.initialBounds.height = this.$el.height();
        moveState.dragCallback = callback;

        this.#$window.on(`mousemove.${this.cid}`, this._onDrag);
    }

    /**
     * End a drag operation.
     */
    _endDragging() {
        /*
         * Unset the dragging flag after the stack unwinds, so that the
         * click event can handle it properly.
         */
        _.defer(() => { this.#moveState.hasMoved = false; });

        this.#$window.off(`mousemove.${this.cid}`);
    }

    /**
     * Move the comment region to a new position.
     *
     * Args:
     *     left (number):
     *         The new X-coordinate of the mouse at the end of the drag
     *         operation, relative to the page.
     *
     *     top (number):
     *         The new Y-coordinate of the mouse at the end of the drag
     *         operation, relative to the page.
     */
    _moveTo(
        left: number,
        top: number,
    ) {
        const region = this.getSelectionRegionSize();
        const maxLeft = region.width - (this.model.get('width') * this.#scale);
        const maxTop = (region.height -
                        (this.model.get('height') * this.#scale));
        const newLeft = (this.#moveState.initialBounds.left +
                         left - this.#moveState.initialCursor.left);
        const newTop = (this.#moveState.initialBounds.top +
                        top - this.#moveState.initialCursor.top);

        this.model.set({
            x: RB.MathUtils.clip(newLeft, 0, maxLeft) / this.#scale,
            y: RB.MathUtils.clip(newTop, 0, maxTop) / this.#scale,
        });
    }

    /*
     * Resize (change with and height of) the comment block.
     *
     * Args:
     *     left (number):
     *         The new X-coordinate of the mouse at the end of the drag
     *         operation, relative to the page.
     *
     *     top (number):
     *         The new Y-coordinate of the mouse at the end of the drag
     *         operation, relative to the page.
     */
    _resizeTo(
        left: number,
        top: number,
    ) {
        const region = this.getSelectionRegionSize();
        const maxWidth = region.width - (this.model.get('x') * this.#scale);
        const maxHeight = region.height - (this.model.get('y') * this.#scale);
        const newWidth = (this.#moveState.initialBounds.width +
                          left - this.#moveState.initialCursor.left);
        const newHeight = (this.#moveState.initialBounds.height +
                           top - this.#moveState.initialCursor.top);

        this.model.set({
            height: RB.MathUtils.clip(newHeight, 0, maxHeight) / this.#scale,
            width: RB.MathUtils.clip(newWidth, 0, maxWidth) / this.#scale,
        });
    }

    /**
     * Handle a mousedown event.
     *
     * Mouse-down means one of these in this view:
     * 1. click
     * 2. start of dragging to move the comment
     * 3. start of dragging to resize the comment
     *
     * This method looks at ``e.target`` and does the appropriate action.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onMouseDown(e: MouseEvent) {
        if (this.model.canUpdateBounds()) {
            e.preventDefault();
            e.stopPropagation();

            let draggingCallback = null;

            if (e.target === this.#$flag.get(0)) {
                draggingCallback = this._moveTo;
            } else if (e.target === this.#$resizeIcon.get(0)) {
                draggingCallback = this._resizeTo;
            }

            if (draggingCallback) {
                this._startDragging(e.pageX, e.pageY, draggingCallback);

                $(window).one('mouseup', this._onWindowMouseUp);
            }
        }
    }

    /**
     * Handle a mouseup event.
     *
     * If something has been dragged, end dragging and update the comment's
     * bounds.
     *
     * If not, the event was actually a ``click`` event and we call the
     * superclass' click handler.
     */
    _onWindowMouseUp() {
        if (this.#moveState.hasMoved) {
            this.model.saveDraftCommentBounds();
        }

        this._endDragging();
    }

    /**
     * Handle a drag event.
     *
     * Set moveState.hasMoved to ``true`` to prevent triggering a ``click``
     * event, and move to view to dragged location.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onDrag(e: MouseEvent) {
        e.preventDefault();
        e.stopPropagation();

        this.hideTooltip();

        this.#moveState.hasMoved = true;
        this.#moveState.dragCallback.call(this, e.pageX, e.pageY);
    }

    /**
     * Render the comment block.
     *
     * Along with the block's rectangle, a floating tooltip will also be
     * created that displays summaries of the comments.
     */
    renderContent() {
        this._updateBounds();

        if (this.model.canUpdateBounds()) {
            this.$el.addClass('can-update-bound');

            this.#$resizeIcon = $('<div class="resize-icon">')
                .appendTo(this.$el);
        }

        this.#$flag = $('<div class="selection-flag">')
            .appendTo(this.$el);

        this._updateCount();
    }

    /**
     * Position the comment dialog to the side of the flag.
     *
     * Args:
     *     commentDlg (RB.CommentDialogView):
     *         The comment dialog.
     */
    positionCommentDlg(commentDlg: CommentDialogView) {
        commentDlg.positionBeside(this.#$flag, {
            fitOnScreen: true,
            side: 'b',
        });
    }

    /**
     * Update the position and size of the comment block element.
     *
     * The new position and size will reflect the x, y, width, and height
     * properties in the model.
     */
    private _updateBounds() {
        this.$el
            .move(this.model.get('x') * this.#scale,
                  this.model.get('y') * this.#scale,
                  'absolute')
            .width(this.model.get('width') * this.#scale)
            .height(this.model.get('height') * this.#scale);
    }

    /**
     * Update the displayed count of comments.
     */
    protected _updateCount() {
        if (this.#$flag) {
            this.#$flag.text(this.model.get('count'));
        }
    }

    /**
     * Handle a click event.
     *
     * If the click event is not the end result of a drag operation, this
     * will emit the "clicked" event on the view.
     */
    protected _onClicked() {
        if (!this.#moveState.hasMoved) {
            this.trigger('clicked');
        }
    }

    /**
     * Set the zoom scale.
     *
     * Args:
     *     scale (number):
     *         A scaling factor. 1.0 is a 1:1 pixel ratio, 0.5 is displayed
     *         at half size, etc.
     */
    setScale(scale: number) {
        this.#scale = scale;
        this._updateBounds();
    }
}
