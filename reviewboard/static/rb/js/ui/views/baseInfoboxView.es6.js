/**
 * An infobox pop-up.
 *
 * This binds to an ``<a>`` element (expected to be either a bug, a user, or a
 * review request right now), and loads the contents of the infobox from a URL
 * built from that element's ``href`` attribute plus the string "infobox/".
 */
RB.BaseInfoboxView = Backbone.View.extend({
    /**
     * The unique ID for the infobox.
     *
     * This will also be used as the CSS class for the infobox.
     */
    infoboxID: null,

    DEFAULT_POSITIONING: {
        side: 'tb',
        xOffset: -20,
        yDistance: 10,
    },

    events: {
        'mouseenter .infobox-hover-item-anchor': '_onHoverItemMouseEnter',
        'mouseleave .infobox-hover-item': '_onHoverItemMouseLeave',
        'mouseenter .infobox-scrollable-section': '_onScrollableMouseEnter',
        'mouseleave .infobox-scrollable-section': '_onScrollableMouseLeave',
    },

    /**
     * Initialize the infobox.
     */
    initialize() {
        /* Set the default positioning. This can be overridden by pages. */
        this.positioning = this.DEFAULT_POSITIONING;

        this._scrollbarWidth = null;
    },

    /**
     * Return the class name for the infobox.
     *
     * Returns:
     *     string:
     *     The CSS class name for the infobox element.
     */
    className() {
        return `infobox ${this.infoboxID}`;
    },

    /**
     * Return the infobox contents URL for a given target.
     *
     * By default, this uses the ``href`` argument on the target, appending
     * ``infobox/``. Infoboxes can override this to provide a different URL.
     */
    getURLForTarget($target) {
        return `${$target.attr('href')}infobox/`;
    },

    /**
     * Set new contents for the infobox.
     *
     * This will replace the HTML of the infobox element and then cause
     * :js:meth:`render` to be called.
     *
     * Args:
     *     html (string):
     *         The new HTML to set.
     */
    setContents(html) {
        this.$el.html(html);
        this.render();
    },

    /**
     * Render the infobox.
     *
     * Subclasses can override this to provide specific rendering. By default,
     * there's no custom rendering performed here.
     *
     * Subclasses should always call the parent method.
     *
     * Returns:
     *     RB.BaseInfoboxView:
     *     This infobox instance, for chaining.
     */
    render() {
        /*
         * We want to be smart about how the scrollbar is handled when
         * hovering over scrollable sections. If we leave this up to CSS,
         * the contents within will either get less space on hover, possibly
         * wrapping (due to the scrollbars appearing), or the window will
         * expand, potentially influencing other elements in the infobox.
         * Neither are good.
         *
         * So what we do is compute the width of the scrollbar and reserve
         * that much space to the right of the content. After we have that,
         * we figure out the natural width for this infobox and then force
         * that width so that the infobox can't unexpectedly widen.
         *
         * When hovering over the scrollable section, the additional padding
         * will go away and the scrollbar will appear, ensuring that neither
         * the content nor the window will alter in size.
         */
        this._scrollbarWidth = null;

        this.$el
            .css('width', '')
            .find('.infobox-scrollable-section')
                .css('padding-right', this._getScrollbarWidth());

        _.defer(() => this.$el.width(this.$el.width()));

        return this;
    },

    /**
     * Return the width of the scrollbar.
     *
     * This will create a temporary off-screen element, measure its width,
     * and then force the display of a scrollbar, and measure that. The
     * difference in widths is the width of the scrollbar.
     *
     * This value may be 0, depending on how the browser renders scrollbars
     * for content. macOS, by default, won't have any measurable width for the
     * scrollbar.
     *
     * Returns:
     *     number:
     *     The width of the scrollbar.
     */
    _getScrollbarWidth() {
        if (this._scrollbarWidth === null) {
            const $el = $('<div>test</div>')
                .css({
                    visibility: 'hidden',
                    position: 'absolute',
                    left: -10000,
                    top: -10000,
                })
                .appendTo(document.body);
            const width = $el.width();

            $el.css('overflow-y', 'scroll');
            const newWidth = $el.width();

            $el.remove();

            this._scrollbarWidth = newWidth - width;
        }

        return this._scrollbarWidth;
    },

    /**
     * Handler for mouseenter events on hover item anchors.
     *
     * This will display the hover details for the item.
     *
     * Args:
     *     evt (Event):
     *         The mouseenter event.
     */
    _onHoverItemMouseEnter(evt) {
        $(evt.target).closest('.infobox-hover-item')
            .addClass('infobox-hover-item-opened');
    },

    /**
     * Handler for mouseleave events on hover items or their children.
     *
     * This will hide the hover details for the item.
     *
     * Args:
     *     evt (Event):
     *         The mouseleave event.
     */
    _onHoverItemMouseLeave(evt) {
        $(evt.target).closest('.infobox-hover-item')
            .removeClass('infobox-hover-item-opened');
    },

    /**
     * Handler for mouseenter events on the description area.
     *
     * This will turn off the padding so the scrollbar has room.
     *
     * Args:
     *     evt (Event):
     *         The mouseenter event.
     */
    _onScrollableMouseEnter(evt) {
        $(evt.target).closest('.infobox-scrollable-section')
            .css('padding-right', 0);
    },

    /**
     * Handler for mouseleave events on the description area.
     *
     * This will re-enable the padding where the scrollbar would be.
     *
     * Args:
     *     evt (Event):
     *         The mouseleave event.
     */
    _onScrollableMouseLeave(evt) {
        $(evt.target).closest('.infobox-scrollable-section')
            .css('padding-right', this._getScrollbarWidth());
    },
});
