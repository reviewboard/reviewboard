/*
 * An abstract base class for revision selector controls. This is extended by
 * the controls used on the diff viewer and file attachment review UI pages.
 */
RB.RevisionSelectorView = Backbone.View.extend({
    template: _.template([
        '<div class="revision-selector">',
        ' <div class="revision-selector-trough" />',
        ' <div class="revision-selector-range" />',
        ' <div class="revision-selector-ticks" />',
        ' <div class="revision-selector-labels" />',
        ' <div class="revision-selector-handles" />',
        '</div>'
    ].join('')),

    events: {
        'mousedown .revision-selector-handle': '_onHandleMouseDown',
        'mousedown .revision-selector-label': '_onLabelMouseDown',
        'click .revision-selector-label': '_onLabelClick'
    },

    /*
     * Initialize the view.
     */
    initialize: function(options) {
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

    /*
     * Render the view.
     */
    render: function(revisionLabels) {
        var i;

        this.$el.html(this.template());

        this._positions = [];
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

        _.each(revisionLabels, function(label, i) {
            var $label;

            $('<div/>')
                .addClass('revision-selector-tick')
                .css('left', this._positions[i] + 'px')
                .appendTo(this._$ticks);

            $label = $('<div/>')
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
        }, this);

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

    /*
     * Update the position of the handles.
     *
     * If a drag is currently active, this will draw using the pending state.
     * Otherwise, it will show the actual revisions.
     */
    _updateHandles: function() {
        var positions = this._positions,
            values;

        if (this._mouseActive) {
            values = this._activeValues;
        } else {
            values = this._values;
        }

        this._$handles.children().each(function(i) {
            $(this).css('left', (positions[values[i]] - 4) + 'px');
        });

        if (this._numHandles === 2) {
            this._$range.css({
                'left': positions[values[0]] + 'px',
                'width': positions[values[1] - values[0]] + 'px'
            });
        }
    },

    /*
     * Callback for when a handle is clicked. Starts a drag.
     *
     * This will register for the various events used to handle the drag
     * operation.
     */
    _onHandleMouseDown: function(ev) {
        var $target = $(ev.currentTarget),
            i;

        this._activeValues = [];
        for (i = 0; i < this._values.length; i++) {
            this._activeValues.push(i);
        }

        this._mouseActive = true;
        this._activeHandle = $target.data('handle-id');

        document.addEventListener('mouseup', this._onHandleMouseUp, true);
        document.addEventListener('mousemove', this._onHandleMouseMove, true);

        $('body').addClass('revision-selector-grabbed');

        ev.preventDefault();
        return false;
    },

    /*
     * Callback for when a mouseup event occurs anywhere.
     *
     * Triggers the 'revisionSelected' event with the new revisions.
     * Removes event handlers used during the drag operation.
     */
    _onHandleMouseUp: function(ev) {
        console.assert(this._mouseActive);

        this._mouseActive = false;
        this._activeHandle = null;

        document.removeEventListener('mouseup', this._onHandleMouseUp, true);
        document.removeEventListener('mousemove', this._onHandleMouseMove, true);

        $('body').removeClass('revision-selector-grabbed');

        if (!_.isEqual(this._activeValues, this._values)) {
            this.trigger('revisionSelected', this._activeValues);
        }

        ev.stopPropagation();
        ev.preventDefault();
    },

    /*
     * Callback for a mousemove event anywhere.
     *
     * Updates the "active" values to select the revisions closest to the
     * current location of the mouse.
     */
    _onHandleMouseMove: function(ev) {
        var positions = this._positions,
            positionsLen = positions.length,
            mouseX,
            i,
            closestPos,
            closestDist,
            dist;

        console.assert(this._mouseActive);

        mouseX = window.pageXOffset + ev.clientX - this._$trough.offset().left;

        for (i = 0; i < positionsLen; i++) {
            dist = Math.abs(positions[i] - mouseX);

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
                this._activeValues[0] = Math.min(closestPos, positionsLen - 2);

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
    }
});
