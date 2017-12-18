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
        'mousedown .revision-selector-handle': '_onHandleMouseDown',
        'mousedown .revision-selector-label': '_onLabelMouseDown',
        'click .revision-selector-label': '_onLabelClick',
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

        _.bindAll(this, '_onHandleMouseUp', '_onHandleMouseMove');
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
            $('<div/>')
                .addClass('revision-selector-tick')
                .css('left', this._positions[i] + 'px')
                .appendTo(this._$ticks);

            const $label = $('<div/>')
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
            $('<div/>')
                .addClass('revision-selector-handle rb-icon rb-icon-range-slider')
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

        this._$handles.children().each((i, el) => {
            $(el).css('left', (positions[values[i]] - 4) + 'px');
        });

        if (this._numHandles === 2) {
            this._$range.css({
                'left': positions[values[0]] + 'px',
                'width': positions[values[1] - values[0]] + 'px',
            });
        }
    },

    /**
     * Callback for when a handle is clicked. Starts a drag.
     *
     * This will register for the various events used to handle the drag
     * operation.
     *
     * Args:
     *     ev (Event):
     *         The mousedown event.
     */
    _onHandleMouseDown(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this._activeValues = [];

        for (let i = 0; i < this._values.length; i++) {
            this._activeValues.push(i);
        }

        this._mouseActive = true;
        this._activeHandle = $(ev.currentTarget).data('handle-id');

        document.addEventListener('mouseup', this._onHandleMouseUp, true);
        document.addEventListener('mousemove', this._onHandleMouseMove, true);

        $('body').addClass('revision-selector-grabbed');
    },

    /**
     * Callback for when a mouseup event occurs anywhere.
     *
     * Triggers the 'revisionSelected' event with the new revisions.
     * Removes event handlers used during the drag operation.
     *
     * Args:
     *     ev (Event):
     *         The mouseup event.
     */
    _onHandleMouseUp(ev) {
        console.assert(this._mouseActive);

        ev.stopPropagation();
        ev.preventDefault();

        this._mouseActive = false;
        this._activeHandle = null;

        document.removeEventListener('mouseup', this._onHandleMouseUp, true);
        document.removeEventListener('mousemove', this._onHandleMouseMove, true);

        $('body').removeClass('revision-selector-grabbed');

        if (!_.isEqual(this._activeValues, this._values)) {
            this.trigger('revisionSelected', this._activeValues);
        }
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
        console.assert(this._mouseActive);

        const mouseX = (window.pageXOffset + ev.clientX -
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
});
