/*
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

    /*
     * Extends super class' events.
     */
    events: _.defaults({
        'click': '_onClicked',
        'mousedown': '_onMouseDown'
    }, RB.AbstractCommentBlockView.prototype.events),

    /*
     * Initializes RegionCommentBlockView.
     */
    initialize: function() {
        this._moveState = {
            hasMoved: false,
            initialCursor: {},
            initialBounds: {},
            dragCallback: _.noop
        };

        _.bindAll(this, '_onDrag', '_onWindowMouseUp');
    },

    /*
     * Override 'delegateEvents', to make this view able to:
     *
     * 1. listen to 'mouseup' event, if the underlying model is movable.
     * 2. listen to the underlying model's 'change' events
     *    to update view accordingly.
     */
    delegateEvents: function() {
        RB.AbstractCommentBlockView.prototype.delegateEvents.call(this);

        this.listenTo(
            this.model,
            'change:x change:y change:width change:height',
            this._updateBounds
        );
        this.listenTo(this.model, 'change:count', this._updateCount);
    },

    /*
     * Override 'delegateEvents', to 'off' events
     * that were 'on'ed in delegateEvents.
     */
    undelegateEvents: function() {
        RB.AbstractCommentBlockView.prototype.undelegateEvents.call(this);

        $(window).off('mousemove', this._onDrag);

        this.stopListening(this.model);
    },

    /*
     * Set the selection region size function.
     *
     * This function is meant to return the maximum size of the selection
     * region for the given comment.
     *
     * Args:
     *     func (Function): A function which will return a size Object.
     */
    setSelectionRegionSizeFunc: function(func) {
        this.selectionRegionSizeFunc = func;
    },

    /*
     * Return the selection region size.
     *
     * Returns:
     *     Object:
     *         An object with ``x``, ``y``, ``width``, and ``height`` fields,
     *         in pixels.
     */
    getSelectionRegionSize: function() {
        return _.result(this, 'selectionRegionSizeFunc');
    },

    /*
     * Calculate and return movable region, based on the selection region size
     * and size of the underlying comment model.
     */
    getMovableRegion: function() {
        var selectionRegionSize = this.getSelectionRegionSize();

        return {
            left: {
                min: 0,
                max: selectionRegionSize.width - this.model.get('width')
            },
            top: {
                min: 0,
                max: selectionRegionSize.height - this.model.get('height')
            }
        };
    },

    /*
     * Calculate and return valid max size of the comment-block's region,
     * based on the selection region size and size of the underlying
     * comment model.
     */
    getValidMaxSize: function() {
        var selectionRegionSize = this.getSelectionRegionSize();

        return {
            width: selectionRegionSize.width - this.model.get('x'),
            height: selectionRegionSize.height - this.model.get('y')
        };
    },

    /*
     * Initialize moveState dictionary.
     *
     * 'hasMoved' is used to distinguish dragging action from clicking.
     * 'initialCursor' and 'initialBounds' are used to calculate new position
     *  and size while dragging.
     */
    _initializeMoveState: function(left, top, callback) {
        var moveState = this._moveState;

        moveState.hasMoved = false;
        moveState.initialCursor.left = left;
        moveState.initialCursor.top = top;
        moveState.initialBounds.left = this.$el.position().left;
        moveState.initialBounds.top = this.$el.position().top;
        moveState.initialBounds.width = this.$el.width();
        moveState.initialBounds.height = this.$el.height();
        moveState.dragCallback = callback;
    },

    /*
     * This method should be called when people seem to start moving the view.
     */
    _startDragging: function(left, top, callback) {
        this._initializeMoveState(left, top, callback);

        $(window).on('mousemove', this._onDrag);
    },

    /*
     * This method should be called when people seem to end moving the view.
     */
    _endDragging: function() {
        /*
         * Unset the dragging flag after the stack unwinds, so that the
         * click event can handle it properly.
         */
        _.defer(_.bind(function() {
            this._moveState.hasMoved = false;
        }, this));

        $(window).off('mousemove', this._onDrag);
    },

    /*
     * Given left and top coordinate, returns a new coordinate which is
     * clipped to the valid selection region.
     */
    _getClippedPosition: function(left, top) {
        var movableRegion = this.getMovableRegion();

        return {
            left: RB.MathUtils.clip(
                left,
                movableRegion.left.min,
                movableRegion.left.max
            ),
            top: RB.MathUtils.clip(
                top,
                movableRegion.top.min,
                movableRegion.top.max
            )
        };
    },

    /*
     * Given width and height, returns a new size which is clipped to the
     * valid selection region.
     */
    _getClippedSize: function(width, height) {
        var maxSize = this.getValidMaxSize();

        return {
            width: RB.MathUtils.clip(width, 0, maxSize.width),
            height: RB.MathUtils.clip(height, 0, maxSize.height)
        };
    },

    /*
     * Moves (change (x, y) coordinate of) the comment-block model to
     * (left, top) of page/window.
     */
    _moveTo: function(left, top) {
        var newPosition = this._getClippedPosition(
            this._moveState.initialBounds.left +
                (left - this._moveState.initialCursor.left),
            this._moveState.initialBounds.top +
                (top - this._moveState.initialCursor.top)
        );

        this.model.set({
            x: newPosition.left,
            y: newPosition.top
        });
    },

    /*
     * Resize (change with and height of) the comment-block model to
     * (left, top) of page/window.
     */
    _resizeTo: function(left, top) {
        var newSize = this._getClippedSize(
            this._moveState.initialBounds.width +
                (left - this._moveState.initialCursor.left),
            this._moveState.initialBounds.height +
                (top - this._moveState.initialCursor.top)
        );

        this.model.set({
            width: newSize.width,
            height: newSize.height
        });
    },

    /*
     * Mouse-down handler.
     *
     * Mouse-down means one of these in this view:
     * 1. click
     * 2. start of dragging to move the comment
     * 3. start of dragging to resize the comment
     *
     * This method looks at e.target and do appropriate action.
     */
    _onMouseDown: function(e) {
        var draggingCallback = null;

        if (this.model.canUpdateBounds()) {
            e.preventDefault();
            e.stopPropagation();

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

    /*
     * Handler for 'mouseup'.
     *
     * If something has been dragged, end dragging and update the comment's
     * bounds.
     *
     * If not, which means the event was actually a 'click' event, call
     * super class's click handler.
     */
    _onWindowMouseUp: function(e) {
        if (this._moveState.hasMoved) {
            this.model.saveDraftCommentBounds();
        }

        this._endDragging();
    },

    /*
     * Handler for 'dragging'.
     *
     * Set moveState.hasMoved to yes to prevent triggering 'click' event, and
     * move to view to dragged location.
     */
    _onDrag: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this.hideTooltip();

        this._moveState.hasMoved = true;
        this._moveState.dragCallback.call(this, e.pageX, e.pageY);
    },

    /*
     * Renders the comment block.
     *
     * Along with the block's rectangle, a floating tooltip will also be
     * created that displays summaries of the comments.
     */
    renderContent: function() {
        this._updateBounds();

        if (this.model.canUpdateBounds()) {
            this.$el.addClass('can-update-bound');

            this._$resizeIcon = $('<div/>')
                .addClass('resize-icon')
                .appendTo(this.$el);
        }

        this._$flag = $('<div/>')
            .addClass('selection-flag')
            .appendTo(this.$el);

        this._updateCount();
    },

    /*
     * Positions the comment dlg to the side of the flag.
     */
    positionCommentDlg: function(commentDlg) {
        commentDlg.positionBeside(this._$flag, {
            side: 'b',
            fitOnScreen: true
        });
    },

    /*
     * Updates the position and size of the comment block.
     *
     * The new position and size will reflect the x, y, width, and height
     * properties in the model.
     */
    _updateBounds: function() {
        var model = this.model;

        this.$el
            .move(model.get('x'), model.get('y'), 'absolute')
            .width(model.get('width'))
            .height(model.get('height'));
    },

    /*
     * Updates the displayed count of comments.
     */
    _updateCount: function() {
        if (this._$flag) {
            this._$flag.text(this.model.get('count'));
        }
    },

    /*
     * Handler for mouse click events.
     *
     * If the click event is not the end result of a drag operation, this
     * will emit the "clicked" event on the view.
     */
    _onClicked: function() {
        if (!this._moveState.hasMoved) {
            this.trigger('clicked');
        }
    }
});
