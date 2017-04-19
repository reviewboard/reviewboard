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
        this._chunkEl = null;
        this._chunkContainerEl = null;
        this._$pageContainer = null;
        this._$window = $(window);
        this._prevWindowWidth = null;
        this._prevTop = null;
        this._prevHeight = null;

        _.bindAll(this, 'updateLayout');
    },

    /*
     * Renders the highlighter to the page.
     *
     * This will create all the border elements and compute any variables
     * we want to keep around for further rendering.
     */
    render: function() {
        this._$window.on('resize.' + this.cid, _.bind(function() {
            var windowWidth = this._$window.width();

            if (windowWidth !== this._prevWindowWidth) {
                this._prevWindowWidth = windowWidth;

                this.updateLayout();
            }
        }, this));

        this._$pageContainer = $('#page-container');

        this.updateLayout();

        return this;
    },

    /*
     * Removes the highlighter from the page and disconnects all events.
     */
    remove: function() {
        _super(this).remove.call(this);

        this._$window.off(this.cid);
    },

    /*
     * Highlights a new chunk element.
     *
     * The borders will surround the chunk element and track its position
     * and size as the page updates.
     */
    highlight: function($chunk) {
        this._chunkEl = $chunk[0];
        this._chunkContainerEl = $chunk.parents('.diff-container')[0];

        this.updateLayout();
    },

    /**
     * Update of the position of the highlighter.
     */
    updateLayout: function() {
        var chunkEl = this._chunkEl,
            changed = false,
            css = {},
            padding,
            top,
            height;

        if (!chunkEl) {
            return;
        }

        /*
         * NOTE: We're hard-coding the border widths (1px) so we don't have to
         *       look them up. The borders aren't directly on the chunk (and
         *       may not even be on a child of this chunk), and it's a bit
         *       slow to look these up.
         */
        top = Math.floor(chunkEl.offsetTop +
                         this._chunkContainerEl.offsetTop + 1);
        height = chunkEl.clientHeight + 1;

        if (top !== this._prevTop) {
            css.top = top;
            this._prevTop = top;
            changed = true;
        }

        if (height !== this._prevHeight) {
            css.height = height;
            this._prevHeight = height;
            changed = true;
        }

        if (changed) {
            /*
             * If the positions of the chunk changed, then it's possible the
             * page container's padding has also changed (zooming in/out), so
             * be safe and recompute.
             *
             * Technically we should compute separately for the left and right
             * sides, but in practice we apply even spacing. Save a
             * calculation, since this happens in resize events.
             */
            padding = this._$pageContainer.getExtents('p', 'l');
            css.left = -padding;
            css.right = -padding;

            this.$el.css(css);
        }
    }
});
