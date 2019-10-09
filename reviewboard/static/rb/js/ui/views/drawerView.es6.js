/**
 * A slide-out drawer for info and actions that overlays the sidebar.
 *
 * Drawers are used to provide optional UI elements that aren't shown by
 * default, but can be activated by some action (a button click or item
 * selections). They're useful for multi-selection DataGrids.
 *
 * These can only be used on pages with a sidebar, as they overlay the
 * sidebar area.
 *
 * Drawers are only meant to be instantiated by :js:class:`RB.PageView`.
 */
RB.DrawerView = Backbone.View.extend({
    className: 'rb-c-drawer',

    /**
     * Initialize the view.
     */
    initialize() {
        this.isVisible = false;

        this.$content = null;
        this._$body = null;
    },

    /**
     * Render the drawer.
     *
     * Returns:
     *     Drawer:
     *     This object, for chaining.
     */
    render() {
        this.$content = $('<div class="rb-c-drawer__content">');
        this._$body = $(document.body);
        this.$el
            .empty()
            .append(this.$content);

        return this;
    },

    /**
     * Show the drawer.
     *
     * This will slide in the drawer and fade out the main sidebar area.
     */
    show() {
        this.isVisible = true;
        this._$body.addClass('js-rb-c-drawer-is-shown');
        this.trigger('visibilityChanged', true);
    },

    /**
     * Hide the drawer.
     *
     * This will slide out the drawer and fade in the main sidebar area.
     */
    hide() {
        this.isVisible = false;
        this._$body.removeClass('js-rb-c-drawer-is-shown');
        this.trigger('visibilityChanged', false);
    },
});
