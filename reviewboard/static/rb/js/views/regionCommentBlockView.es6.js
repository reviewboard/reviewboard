/**
 * Provides a visual region over an image or other document showing comments.
 *
 * This will show a selection rectangle over part of an image or other
 * content indicating there are comments there. It will also show the
 * number of comments, along with a tooltip showing comment summaries.
 *
 * This is meant to be used with a RegionCommentBlock model.
 */
RB.RegionCommentBlockView = RB.AbstractCommentBlockView.extend({
    className: 'selection',

    events: _.defaults({
        'click': '_onClicked',
        'mousedown': '_onMouseDown'
    }, RB.AbstractCommentBlockView.prototype.events),

    /**
     * Initialize RegionCommentBlockView.
     */
    initialize() {
        this._scale = 1.0;
        this._moveState = {
            hasMoved: false,
            initialCursor: {},
            initialBounds: {},
            dragCallback: _.noop
        };

        _.bindAll(this, '_onDrag', '_onWindowMouseUp');
    },

    /**
     * Listen to events.
     */
    delegateEvents() {
        RB.AbstractCommentBlockView.prototype.delegateEvents.call(this);

        this.listenTo(
            this.model,
            'change:x change:y change:width change:height',
            this._updateBounds
        );
        this.listenTo(this.model, 'change:count', this._updateCount);
    },

    /**
     * Un-listen to events.
     */
    undelegateEvents() {
        RB.AbstractCommentBlockView.prototype.undelegateEvents.call(this);

        $(window).off('mousemove', this._onDrag);

        this.stopListening(this.model);
    },

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
    setSelectionRegionSizeFunc(func) {
        this.selectionRegionSizeFunc = func;
    },

    /**
     * Return the selection region size.
     *
     * Returns:
     *     object:
     *     An object with ``x``, ``y``, ``width``, and ``height`` fields, in
     *     pixels.
     */
    getSelectionRegionSize() {
        return _.result(this, 'selectionRegionSizeFunc');
    },

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
    _startDragging(left, top, callback) {
        /*
         * ``hasMoved`` is used to distinguish dragging from clicking.
         * ``initialCursor`` and ``initialBounds`` are used to calculate the
         * new position and size while dragging.
         */
        this._moveState.hasMoved = false;
        this._moveState.initialCursor.left = left;
        this._moveState.initialCursor.top = top;
        this._moveState.initialBounds.left = this.$el.position().left;
        this._moveState.initialBounds.top = this.$el.position().top;
        this._moveState.initialBounds.width = this.$el.width();
        this._moveState.initialBounds.height = this.$el.height();
        this._moveState.dragCallback = callback;

        $(window).on('mousemove', this._onDrag);
    },

    /**
     * End a drag operation.
     */
    _endDragging() {
        /*
         * Unset the dragging flag after the stack unwinds, so that the
         * click event can handle it properly.
         */
        _.defer(() => { this._moveState.hasMoved = false; });

        $(window).off('mousemove', this._onDrag);
    },

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
    _moveTo(left, top) {
        const region = this.getSelectionRegionSize();
        const maxLeft = region.width - (this.model.get('width') * this._scale);
        const maxTop = region.height - (this.model.get('height') * this._scale);
        const newLeft = (this._moveState.initialBounds.left +
                         left - this._moveState.initialCursor.left);
        const newTop = (this._moveState.initialBounds.top +
                        top - this._moveState.initialCursor.top);

        this.model.set({
            x: RB.MathUtils.clip(newLeft, 0, maxLeft) / this._scale,
            y: RB.MathUtils.clip(newTop, 0, maxTop) / this._scale
        });
    },

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
    _resizeTo(left, top) {
        const region = this.getSelectionRegionSize();
        const maxWidth = region.width - (this.model.get('x') * this._scale);
        const maxHeight = region.height - (this.model.get('y') * this._scale);
        const newWidth = (this._moveState.initialBounds.width +
                          left - this._moveState.initialCursor.left);
        const newHeight = (this._moveState.initialBounds.height +
                           top - this._moveState.initialCursor.top);

        this.model.set({
            width: RB.MathUtils.clip(newWidth, 0, maxWidth) / this._scale,
            height: RB.MathUtils.clip(newHeight, 0, maxHeight) / this._scale
        });
    },

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
    _onMouseDown(e) {
        if (this.model.canUpdateBounds()) {
            e.preventDefault();
            e.stopPropagation();

            let draggingCallback = null;
            if (e.target === this._$flag.get(0)) {
                draggingCallback = this._moveTo;
            } else if (e.target === this._$resizeIcon.get(0)) {
                draggingCallback = this._resizeTo;
            }

            if (draggingCallback) {
                this._startDragging(e.pageX, e.pageY, draggingCallback);

                $(window).one('mouseup', this._onWindowMouseUp);
            }
        }
    },

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
        if (this._moveState.hasMoved) {
            this.model.saveDraftCommentBounds();
        }

        this._endDragging();
    },

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
    _onDrag(e) {
        e.preventDefault();
        e.stopPropagation();

        this.hideTooltip();

        this._moveState.hasMoved = true;
        this._moveState.dragCallback.call(this, e.pageX, e.pageY);
    },

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

            this._$resizeIcon = $('<div class="resize-icon" />')
                .appendTo(this.$el);
        }

        this._$flag = $('<div class="selection-flag" />')
            .appendTo(this.$el);

        this._updateCount();
    },

    /**
     * Position the comment dialog to the side of the flag.
     *
     * Args:
     *     commentDlg (RB.CommentDialogView):
     *         The comment dialog.
     */
    positionCommentDlg(commentDlg) {
        commentDlg.positionBeside(this._$flag, {
            side: 'b',
            fitOnScreen: true
        });
    },

    /**
     * Update the position and size of the comment block element.
     *
     * The new position and size will reflect the x, y, width, and height
     * properties in the model.
     */
    _updateBounds() {
        this.$el
            .move(this.model.get('x') * this._scale,
                  this.model.get('y') * this._scale,
                  'absolute')
            .width(this.model.get('width') * this._scale)
            .height(this.model.get('height') * this._scale);
    },

    /**
     * Update the displayed count of comments.
     */
    _updateCount() {
        if (this._$flag) {
            this._$flag.text(this.model.get('count'));
        }
    },

    /**
     * Handle a click event.
     *
     * If the click event is not the end result of a drag operation, this
     * will emit the "clicked" event on the view.
     */
    _onClicked() {
        if (!this._moveState.hasMoved) {
            this.trigger('clicked');
        }
    },

    /**
     * Set the zoom scale.
     *
     * Args:
     *     scale (number):
     *         A scaling factor. 1.0 is a 1:1 pixel ratio, 0.5 is displayed
     *         at half size, etc.
     */
    setScale(scale) {
        this._scale = scale;
        this._updateBounds();
    }
});
