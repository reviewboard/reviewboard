/*
 * A view that allows users to select a revision of the diff to view.
 */
RB.DiffRevisionSelectorView = Backbone.View.extend({
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
    initialize: function() {
        this._rendered = false;
        this._mouseActive = false;
        this._activeHandle = null;
        this._values = [];
        this.listenTo(this.model, 'change', this._update);

        _.bindAll(this, '_onHandleMouseUp', '_onHandleMouseMove');
    },

    /*
     * Render the view.
     */
    render: function() {
        var labels = ['orig'],
            i;

        this.$el.html(this.template());

        // New
        this._positions = [0];
        for (i = 1; i <= this.options.numDiffs; i++) {
            // Ticks are spaced 30px apart.
            this._positions.push(i * 30);
            labels.push(i.toString());
        }

        this._$trough = this.$('.revision-selector-trough')
            .width(this._positions[this.options.numDiffs]);

        this._$range = this.$('.revision-selector-range');

        this._$ticks = this.$('.revision-selector-ticks');
        this._$labels = this.$('.revision-selector-labels');
        _.each(labels, function(label, i) {
            var $label;

            $('<div/>')
                .addClass('revision-selector-tick')
                .css('left', this._positions[i] + 'px')
                .appendTo(this._$ticks);

            $label = $('<div/>')
                .text(label)
                .addClass('revision-selector-label')
                .appendTo(this._$labels);
            if (i > 0) {
                $label
                    .data('revision', i)
                    .addClass('revision-selector-label-active');
            }
            $label.css('left', (this._positions[i] - ($label.width() / 2)) + 'px');
        }, this);

        this._$handles = this.$('.revision-selector-handles');
        for (i = 0; i < 2; i++) {
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
     * Update the displayed revision based on the model.
     */
    _update: function() {
        var revision = this.model.get('revision'),
            interdiffRevision = this.model.get('interdiffRevision');

        this._values = [
            interdiffRevision ? revision : 0,
            interdiffRevision ? interdiffRevision : revision
        ];

        if (!this._rendered) {
            return;
        }

        // New
        this._updateHandles();
    },

    /*
     * Update the position of the handles.
     *
     * If a drag is currently active, this will draw using the pending state.
     * Otherwise, it will show the actual revisions shown in the diff.
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
        this._$range.css({
            'left': positions[values[0]] + 'px',
            'width': positions[values[1] - values[0]] + 'px'
        });
    },

    /*
     * Callback for when a single revision is selected.
     */
    _onRevisionSelected: function(ev) {
        var $target = $(ev.currentTarget);
        this.trigger('revisionSelected', 0, $target.data('revision'));
    },

    /*
     * Callback for when an interdiff is selected.
     */
    _onInterdiffSelected: function(ev) {
        var $target = $(ev.currentTarget);
        this.trigger('revisionSelected',
                     $target.data('first-revision'),
                     $target.data('second-revision'));
    },

    /*
     * Callback for when one of the handles is clicked. Starts a drag.
     *
     * This will register for the various events used to handle the drag
     * operation.
     */
    _onHandleMouseDown: function(ev) {
        var $target = $(ev.currentTarget);

        this._mouseActive = true;
        this._activeHandle = $target.data('handle-id');
        this._activeValues = [
            this._values[0],
            this._values[1]
        ];

        document.addEventListener('mouseup', this._onHandleMouseUp, true);
        document.addEventListener('mousemove', this._onHandleMouseMove, true);

        $('body').addClass('revision-selector-grabbed');

        ev.preventDefault();
        return false;
    },

    /*
     * Callback for when a mouseup event occurs anywhere.
     *
     * Triggers the 'revisionSelected' event with the new revision and
     * interdiff revision. Removes event handlers used during the drag
     * operation.
     */
    _onHandleMouseUp: function(ev) {
        console.assert(this._mouseActive);

        this._mouseActive = false;
        this._activeHandle = null;

        document.removeEventListener('mouseup', this._onHandleMouseUp, true);
        document.removeEventListener('mousemove', this._onHandleMouseMove, true);

        $('body').removeClass('revision-selector-grabbed');

        if (this._activeValues[0] !== this._values[0] ||
            this._activeValues[1] !== this._values[1]) {
            this.trigger('revisionSelected',
                         this._activeValues[0], this._activeValues[1]);
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

        if (this._activeHandle === 0) {
            this._activeValues[0] = Math.min(closestPos, positionsLen - 2);

            if (this._values[1] <= this._activeValues[0]) {
                this._activeValues[1] = this._activeValues[0] + 1;
            } else {
                this._activeValues[1] = this._values[1];
            }
        } else if (this._activeHandle === 1) {
            this._activeValues[1] = Math.max(closestPos, 1);

            if (this._values[0] >= this._activeValues[1]) {
                this._activeValues[0] = this._activeValues[1] - 1;
            } else {
                this._activeValues[0] = this._values[0];
            }
        }
        this._updateHandles();
    },

    /*
     * Callback for when one of the labels is clicked.
     *
     * This will jump to the target revision.
     *
     * TODO: we should allow people to click and drag over a range of labels to
     * select an interdiff.
     */
    _onLabelClick: function(ev) {
        var $target = $(ev.currentTarget);

        this.trigger('revisionSelected', 0, $target.data('revision'));
    }
});
