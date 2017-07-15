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

    /**
     * Initialize the infobox.
     */
    initialize() {
        /* Set the default positioning. This can be overridden by pages. */
        this.positioning = this.DEFAULT_POSITIONING;
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
     * Returns:
     *     RB.BaseInfoboxView:
     *     This infobox instance, for chaining.
     */
    render() {
        return this;
    },
});

