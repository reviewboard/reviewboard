/**
 * An abstract base class for revision selector controls. This is extended by
 * the controls used on the diff viewer and file attachment review UI pages.
 */
RB.RevisionSelectorView = Backbone.View.extend({
    template: _.template(dedent`
        <div class="revision-selector">
         <div class="revision-selector-trough"></div>
         <div class="revision-selector-range"></div>
         <div class="revision-selector-ticks"></div>
         <div class="revision-selector-labels"></div>
         <div class="revision-selector-handles"></div>
        </div>
    `),

    events: {
        'click .revision-selector-label': '_onLabelClick',
        'mousedown .revision-selector-handle': '_onHandleMouseDown',
        'mousedown .revision-selector-label': '_onLabelMouseDown',
        'touchstart .revision-selector-handle': '_onHandleTouchStart',
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     firstLabelActive (boolean):
     *         Whether the first label should be an active (selectable)
     *         revision or not.
     *
     *     numHandles (number):
     *         The number of revision slider handles to show.
     */
    initialize(options) {
        console.assert(_.isObject(options));
        console.assert(options.numHandles === 1 || options.numHandles === 2);

        this._activeHandle = null;
        this._firstLabelActive = options.firstLabelActive;
        this._mouseActive = false;
        this._numHandles = options.numHandles;
        this._values = [];

        this._rendered = false;

        this.listenTo(this.model, 'change', this._update);

        _.bindAll(this,
                  '_onHandleMouseUp',
                  '_onHandleMouseMove',
                  '_onHandleTouchEnd',
                  '_onHandleTouchMove');
    },

    /**
     * Render the view.
     *
     * Args:
     *     revisionLabels (Array):
     *         The labels to use for each revision.
     *
     * Returns:
     *     RB.RevisionSelectorView:
     *     This object, for chaining.
     */
    render(revisionLabels) {
        this.$el.html(this.template());

        this._positions = [];

        let i;

        for (i = 0; i < revisionLabels.length; i++) {
            // Ticks are spaced 30px apart.
            this._positions.push(i * 30);
        }

        this._$handles = this.$('.revision-selector-handles');
        this._$range = this.$('.revision-selector-range');
        this._$ticks = this.$('.revision-selector-ticks');
        this._$labels = this.$('.revision-selector-labels');
        this._$trough = this.$('.revision-selector-trough')
            .width(this._positions[i - 1]);

        _.each(revisionLabels, (label, i) => {
            $('<div>')
                .addClass('revision-selector-tick')
                .css('left', this._positions[i] + 'px')
                .appendTo(this._$ticks);

            const $label = $('<div>')
                .text(label)
                .addClass('revision-selector-label')
                .appendTo(this._$labels);

            $label.css('left', (this._positions[i] -
                                ($label.width() / 2)) + 'px');

            if (this._firstLabelActive || i > 0) {
                $label
                    .data('revision', i)
                    .addClass('revision-selector-label-active');
            }
        });

        for (i = 0; i < this._numHandles; i++) {
            $('<div>')
                .addClass(
                    'revision-selector-handle rb-icon rb-icon-range-slider')
                .data('handle-id', i)
                .appendTo(this._$handles);
        }

        this._rendered = true;
        this._update();

        return this;
    },

    /**
     * Update the position of the handles.
     *
     * If a drag is currently active, this will draw using the pending state.
     * Otherwise, it will show the actual revisions.
     */
    _updateHandles() {
        const positions = this._positions;
        const values = this._mouseActive ? this._activeValues
                                         : this._values;
        let handleOffset = null;

        this._$handles.children().each((i, el) => {
            const $el = $(el);

            if (handleOffset === null) {
                handleOffset = Math.floor($el.width() / 2);
            }

            const left = (positions[values[i]] - handleOffset);

            $el.css('left', `${left}px`);
        });

        if (this._numHandles === 2) {
            this._$range.css({
                'left': positions[values[0]] + 'px',
                'width': positions[values[1] - values[0]] + 'px',
            });
        }
    },

    /**
     * Begin dragging a handle.
     *
     * This will prepare state for dragging the provided handle.
     *
     * Args:
     *     $handle (jQuery):
     *         The handle being dragged.
     */
    _beginDragHandle($handle) {
        const activeValues = [];

        for (let i = 0; i < this._values.length; i++) {
            activeValues.push(i);
        }

        this._activeValues = activeValues;

        this._mouseActive = true;
        this._activeHandle = $handle.data('handle-id');

        $('body').addClass('revision-selector-grabbed');
    },

    /**
     * Finish dragging a handle.
     *
     * This will reset the drag state and emit the ``revisionSelected``
     * event if the handle is in a new location.
     */
    _endDragHandle() {
        console.assert(this._mouseActive);

        this._mouseActive = false;
        this._activeHandle = null;

        $('body').removeClass('revision-selector-grabbed');

        if (!_.isEqual(this._activeValues, this._values)) {
            this.trigger('revisionSelected', this._activeValues);
        }
    },

    /**
     * Move a handle based on a drag operation.
     *
     * This will update the displayed handles if needed in order to represent
     * any new drag locations.
     *
     * Args:
     *     clientX (number):
     *         The current dragged location for the handle.
     */
    _moveDragHandle(clientX) {
        console.assert(this._mouseActive);

        const mouseX = (window.pageXOffset + clientX -
                        this._$trough.offset().left);
        let closestPos;
        let closestDist;

        for (let i = 0; i < this._positions.length; i++) {
            const dist = Math.abs(this._positions[i] - mouseX);

            if (closestDist === undefined || dist < closestDist) {
                closestDist = dist;
                closestPos = i;
            }
        }

        if (this._numHandles === 1) {
            this._activeValues[0] = closestPos;
        } else if (this._numHandles === 2) {
            /*
             * The two-handle case is complex, because we always want the first
             * value to be less than the second. The below creates a "pushing"
             * behavior where if you slide the left handle to the right, it
             * will "push" the right handle to always have a span of at least
             * one revision, and vice-versa.
             */
            if (this._activeHandle === 0) {
                // Pushing to the right
                this._activeValues[0] = Math.min(
                    closestPos, this._positions.length - 2);

                if (this._values[1] <= this._activeValues[0]) {
                    this._activeValues[1] = this._activeValues[0] + 1;
                } else {
                    this._activeValues[1] = this._values[1];
                }
            } else if (this._activeHandle === 1) {
                // Pushing to the left
                this._activeValues[1] = Math.max(closestPos, 1);

                if (this._values[0] >= this._activeValues[1]) {
                    this._activeValues[0] = this._activeValues[1] - 1;
                } else {
                    this._activeValues[0] = this._values[0];
                }
            }
        }

        this._updateHandles();
    },

    /**
     * Callback for when a mousedown event occurs on a handle.
     *
     * This will register for the various events used to handle the drag
     * operation via the mouse for the revision handle.
     *
     * Args:
     *     ev (Event):
     *         The mousedown event.
     */
    _onHandleMouseDown(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this._beginDragHandle($(ev.currentTarget));

        document.addEventListener('mouseup', this._onHandleMouseUp, true);
        document.addEventListener('mousemove', this._onHandleMouseMove, true);
    },

    /**
     * Callback for when a touchstart event occurs on a handle.
     *
     * This will register for the various events used to handle the drag
     * operation via touchscreens for the revision handle.
     *
     * Args:
     *     ev (Event):
     *         The touchstart event.
     */
    _onHandleTouchStart(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this._beginDragHandle($(ev.targetTouches[0].target));

        document.addEventListener('touchend', this._onHandleTouchEnd, true);
        document.addEventListener('touchmove', this._onHandleTouchMove, true);
    },

    /**
     * Callback for when a mouseup event occurs anywhere.
     *
     * This completes the handle drag operation and then triggers the
     * ``revisionSelected`` event with the new revisions.
     *
     * All current mouse events will be cleaned up.
     *
     * Args:
     *     ev (Event):
     *         The mouseup event.
     */
    _onHandleMouseUp(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        document.removeEventListener('mouseup', this._onHandleMouseUp, true);
        document.removeEventListener('mousemove', this._onHandleMouseMove,
                                     true);

        this._endDragHandle();
    },

    /**
     * Callback for when a touchend event occurs anywhere.
     *
     * This completes the handle drag operation and then triggers the
     * ``revisionSelected`` event with the new revisions.
     *
     * All current mouse events will be cleaned up.
     *
     * Args:
     *     ev (Event):
     *         The touchend event.
     */
    _onHandleTouchEnd(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        document.removeEventListener('touchend', this._onHandleTouchEnd, true);
        document.removeEventListener('touchmove', this._onHandleTouchMove,
                                     true);

        this._endDragHandle();
    },

    /**
     * Callback for a mousemove event anywhere.
     *
     * Updates the "active" values to select the revisions closest to the
     * current location of the mouse.
     *
     * Args:
     *     ev (Event):
     *         The mousemove event.
     */
    _onHandleMouseMove(ev) {
        this._moveDragHandle(ev.clientX);
    },

    /**
     * Callback for a touchmove event anywhere.
     *
     * Updates the "active" values to select the revisions closest to the
     * current location of the mouse.
     *
     * Args:
     *     ev (Event):
     *         The touchmove event.
     */
    _onHandleTouchMove(ev) {
        this._moveDragHandle(ev.targetTouches[0].clientX);
    },
});
