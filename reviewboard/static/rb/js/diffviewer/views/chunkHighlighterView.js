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
        this._$top = null;
        this._$bottom = null;
        this._$left = null;
        this._$right = null;
        this._borderWidth = null;
        this._borderHeight = null;
        this._borderOffsetX = null;
        this._borderOffsetY = null;

        this._resetState();

        _.bindAll(this, '_queueUpdatePosition', '_updatePosition');
    },

    /*
     * Renders the highlighter to the page.
     *
     * This will create all the border elements and compute any variables
     * we want to keep around for further rendering.
     */
    render: function() {
        var $border = $('<div class="diff-highlight-border"/>');

        this._$top = $border.clone().appendTo(this.$el);
        this._$bottom = $border.clone().appendTo(this.$el);
        this._$left = $border.clone().appendTo(this.$el);
        this._$right = $border.clone().appendTo(this.$el);

        this._borderWidth = this._$left.width();
        this._borderHeight = this._$top.height();
        this._borderOffsetX = this._borderWidth / 2;
        this._borderOffsetY = this._borderHeight / 2;

        if ($.browser.msie) {
            if ($.browser.version <= 9) {
                /* On IE <= 9, the black rectangle is too far to the top. */
                this._borderOffsetY = 0;
            } else {
                /* On IE >= 10, the black rectangle is too far down. */
                this._borderOffsetY = this._borderHeight;
            }

            if ($.browser.version === 8) {
                /* And on IE8, it's also too far to the left. */
                this._borderOffsetX = -this._borderOffsetX;
            }
        }

        $(window).on('resize.' + this.cid, _.bind(function() {
            /*
             * Other operations may impact the size of the page, so do this
             * after all resize handlers have been called.
             */
            _.defer(this._updatePosition);
        }, this));

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
        this._queueUpdatePosition();
    },

    /*
     * Resets the calculated state for a chunk.
     */
    _resetState: function() {
        this._$chunk = null;
        this._oldTop = null;
        this._oldWidth = null;
        this._oldHeight = null;
    },

    /*
     * Updates the position of the borders, based on the chunk dimensions.
     */
    _updatePosition: function(e) {
        var $container,
            offset,
            top,
            width,
            height,
            outerHeight,
            outerWidth,
            outerTop;

        if (e && e.target && e.target !== window &&
            !e.target.getElementsByTagName) {
            /*
             * This is not a container. It might be a text node.
             * Ignore it.
             */
            return;
        }

        offset = this._$chunk.position();

        if (!offset) {
            return;
        }

        $container = this._$chunk.parents('.diff-container');

        /*
         * Attach the element to the container, so it'll move along with
         * the container if anything above moves.
         */
        this.$el
            .remove()
            .appendTo($container);

        top = Math.floor(offset.top);
        width = $container.outerWidth();
        height = this._$chunk.outerHeight();

        if (top === this._oldTop &&
            width === this._oldWidth &&
            height === this._oldHeight) {
            /* The position and size haven't actually changed. */
            return;
        }

        outerHeight = height + this._borderOffsetX;
        outerWidth  = width - this._borderWidth;
        outerTop    = top - this._borderOffsetY;

        this._$left.css({
            left: 0,
            top: outerTop,
            height: outerHeight
        });

        this._$top.css({
            left: 0,
            top: outerTop,
            width: outerWidth
        });

        this._$right.css({
            left: outerWidth,
            top: outerTop,
            height: outerHeight
        });

        this._$bottom.css({
            left: 0,
            top: outerTop + outerHeight,
            width: outerWidth + this._borderWidth
        });

        this._oldTop = top;
        this._oldWidth = width;
        this._oldHeight = height;
    },

    /*
     * Queues an update of the border positions.
     *
     * Since this may be called many times in quick succession, it will
     * only ever actually trigger updating the position when the events
     * have calmed down. It has a 50ms throttle.
     */
    _queueUpdatePosition: _.debounce(function(e) {
        this._updatePosition(e);
    }, 50)
}, {
    _instance: null,

    /*
     * Highlights a chunk on the page.
     *
     * If a highlighter isn't already created, this will create one.
     */
    highlight: function($chunk) {
        if (!$chunk || $chunk.length === 0) {
            return;
        }

        if (!this._instance) {
            this._instance = new RB.ChunkHighlighterView();

            /*
             * This placement is temporary, in order to calculate the
             * sizes and offsets. It will be moved in the highlight call
             * below.
             */
            this._instance.$el.appendTo($('#diffs'));
            this._instance.render();
        }

        this._instance.highlight($chunk);
    }
});
