/*
 * Highlights a chunk of the diff.
 *
 * This will create and move four border elements around the chunk. We use
 * these border elements instead of setting a border since few browsers
 * render borders on <tbody> tags the same, and give us few options for
 * styling.
 *
 * In practice, there's only ever one highlighter on a page at a time.
 */
RB.ChunkHighlighterView = Backbone.View.extend({
    className: 'diff-highlight',

    /*
     * Initializes the highlighter.
     */
    initialize: function() {
        this._resetState();
        this._$pageContainer = null;
        this._width = null;

        _.bindAll(this, '_updatePosition');
    },

    /*
     * Renders the highlighter to the page.
     *
     * This will create all the border elements and compute any variables
     * we want to keep around for further rendering.
     */
    render: function() {
        $(window).on('resize.' + this.cid, _.throttle(_.bind(function() {
            this._recalcGlobalSizes();
            this._resetChunkSizes();

            /*
             * Other operations may impact the size of the page, so do this
             * after all resize handlers have been called.
             */
            _.defer(this._updatePosition);
        }, this)));

        this._$pageContainer = $('#page-container');

        this._recalcGlobalSizes();

        return this;
    },

    /*
     * Removes the highlighter from the page and disconnects all events.
     */
    remove: function() {
        _super(this).remove.call(this);

        $(window).off(this.cid);
    },

    /*
     * Highlights a new chunk element.
     *
     * The borders will surround the chunk element and track its position
     * and size as the page updates.
     */
    highlight: function($chunk) {
        this._resetState();

        this._$chunk = $chunk;
        this._$chunkContainer = $chunk.parents('.diff-container');

        this._updatePosition();
    },

    /*
     * Resets the calculated state for a chunk.
     */
    _resetState: function() {
        this._$chunk = null;
        this._$chunkContainer = null;

        this._resetChunkSizes();
    },

    /*
     * Resets the calculated offsets and sizes for a chunk.
     */
    _resetChunkSizes: function() {
        this._top = null;
        this._height = null;
    },

    /*
     * Re-calculates the common sizes for the page container.
     */
    _recalcGlobalSizes: function() {
        var oldWidth = this.$el.width();

        this._width = this._$pageContainer.outerWidth();

        this.$el.css({
            left: -this._$pageContainer.getExtents('p', 'l'),
            width: oldWidth
        });
    },

    /*
     * Updates the position of the borders, based on the chunk dimensions.
     */
    _updatePosition: function(e) {
        var chunkPos;

        if (e && e.target && e.target !== window &&
            !e.target.getElementsByTagName) {
            /*
             * This is not a container. It might be a text node.
             * Ignore it.
             */
            return;
        }

        if (this._$chunk === null) {
            return;
        }

        if (this._top === null) {
            chunkPos = this._$chunk.position();

            if (!chunkPos) {
                /* The diff isn't yet loaded. */
                return;
            }

            this._top = Math.floor(chunkPos.top +
                                   this._$chunkContainer.position().top);
        }

        if (this._height === null) {
            this._height = this._$chunk.outerHeight();
        }

        if (this._top === this._oldTop &&
            this._width === this._oldWidth &&
            this._height === this._oldHeight) {
            /* The position and size haven't actually changed. */
            return;
        }

        this.$el.css({
            top: this._top,
            height: this._height + 1,  // Compensate for the tbody border below.
            width: this._width
        });

        this._oldTop = this._top;
        this._oldWidth = this._width;
        this._oldHeight = this._height;
    }
});
