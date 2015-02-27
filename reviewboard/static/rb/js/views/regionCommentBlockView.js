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
        'mousedown': '_onMouseDown'
    }, _super(this).events),

    /*
     * Initializes RegionCommentBlockView.
     */
    initialize: function() {
        this.moveState = {
            hasMoved: false,
            initialCursor: {},
            initialBounds: {},
            dragCallback: _.noop
        };
        _.bindAll(this, '_onDrag', '_onWindowMouseUp');
    },

    /*
     * Initialize moveState dictionary.
     *
     * 'hasMoved' is used to distinguish dragging action from clicking.
     * 'initialCursor' and 'initialBounds' are used to calculate new position
     *  and size while dragging.
     */
    initializeMoveState: function(left, top, callback) {
        this.moveState.hasMoved = false;
        this.moveState.initialCursor.left = left;
        this.moveState.initialCursor.top = top;
        this.moveState.initialBounds.left = this.$el.position().left;
        this.moveState.initialBounds.top = this.$el.position().top;
        this.moveState.initialBounds.width = this.$el.width();
        this.moveState.initialBounds.height = this.$el.height();
        this.moveState.dragCallback = callback;
    },

    /*
     * This method should be called when people seem to start moving the view.
     */
    startDragging: function(left, top, callback) {
        this.initializeMoveState(left, top, callback);
        $(window).on('mousemove', this._onDrag);
    },

    /*
     * This method should be called when people seem to end moving the view.
     */
    endDragging: function() {
        this.moveState.hasMoved = false;
        $(window).off('mousemove', this._onDrag);
    },

    /*
     * Given left and top coordinate, returns a new coordinate which is
     * clipped to the valid selection region.
     */
    getClippedPosition: function(left, top) {
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
    getClippedSize: function(width, height) {
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
    moveTo: function(left, top) {
        var newPosition = this.getClippedPosition(
            this.moveState.initialBounds.left +
                (left - this.moveState.initialCursor.left),
            this.moveState.initialBounds.top +
                (top - this.moveState.initialCursor.top)
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
    resizeTo: function(left, top) {
        var newSize = this.getClippedSize(
            this.moveState.initialBounds.width +
                (left - this.moveState.initialCursor.left),
            this.moveState.initialBounds.height +
                (top - this.moveState.initialCursor.top)
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
     *
     */
    _onMouseDown: function(e) {
        $(window).one('mouseup', this._onWindowMouseUp);
        e.preventDefault();
        e.stopPropagation();

        if (this.model.canUpdateBounds()) {
            var draggingCallback = null;

            if (e.target === this._$flag.get(0)) {
                draggingCallback = this.moveTo;
            } else if (e.target === this._$resizeIcon.get(0)) {
                draggingCallback = this.resizeTo;
            }

            if (draggingCallback) {
                this.startDragging(e.pageX, e.pageY, draggingCallback);
            }
        }
    },

    /*
     * Handler for 'mouseup'.
     *
     * If something has been dragged, end dragging and update the comment's
     * bounds.
     * If not, which means the event was actually a 'click' event, call
     * super class's click handler.
     */
    _onWindowMouseUp: function() {
        if (this.moveState.hasMoved) {
            this.model.saveDraftCommentBounds();
        } else {
            _super(this)._onClicked.call(this);
        }
        this.endDragging();
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
        this.moveState.hasMoved = true;
        this.moveState.dragCallback.call(this, e.pageX, e.pageY);
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
     * Override 'delegateEvents', to make this view able to:
     *
     * 1. listen to 'mouseup' event, if the underlying model is movable.
     * 2. listen to the underlying model's 'change' events
     *    to update view accordingly.
     */
    delegateEvents: function() {
        _super(this).delegateEvents.call(this);

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
        _super(this).undelegateEvents.call(this);

        $(window).off('mousemove', this._onDrag);

        this.stopListening(this.model);
    },

    /*
     * Setter for selectionRegionSize. This property is used to limit
     * the position/size of the underlying comment mode.
     */
    setSelectionRegionSize: function(value) {
        this.selectionRegionSize = value;
    },

    /*
     * Getter for selectionRegionSize.
     */
    getSelectionRegionSize: function() {
        return _.result(this, 'selectionRegionSize');
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
     * Ignore click event. Click must be handled by 'mousedown' and 'mouseup'
     * event handlers in this view.
     */
    _onClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();
        return;
    }
});
