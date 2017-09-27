/**
 * Represents an entry on the review request page.
 */
RB.ReviewRequestPage.EntryView = Backbone.View.extend({
    events: {
        'click .collapse-button': '_onToggleCollapseClicked',
    },

    /**
     * Render the box.
     *
     * Returns:
     *     RB.ReviewRequestPage.EntryView:
     *     This object, for chaining.
     */
    render() {
        this._$box = this.$('.review-request-page-entry-contents');
        this._$expandCollapseButton = this.$('.collapse-button .rb-icon');

        if (this._$box.hasClass('collapsed')) {
            this._$expandCollapseButton.addClass('rb-icon-expand-review');
        } else {
            this._$expandCollapseButton.addClass('rb-icon-collapse-review');
        }

        return this;
    },

    /**
     * Return whether the entry is currently collapsed.
     *
     * Returns:
     *     boolean:
     *     ``True`` if the entry is currently collapsed. ``False`` if expanded.
     */
    isCollapsed() {
        return this._$box.hasClass('collapsed');
    },

    /**
     * Expand the box.
     */
    expand() {
        this._$box.removeClass('collapsed');
        this._$expandCollapseButton
            .removeClass('rb-icon-expand-review')
            .addClass('rb-icon-collapse-review');

        this.model.set('collapsed', false);
    },

    /**
     * Collapse the box.
     */
    collapse() {
        this._$box.addClass('collapsed');
        this._$expandCollapseButton
            .removeClass('rb-icon-collapse-review')
            .addClass('rb-icon-expand-review');

        this.model.set('collapsed', true);
    },

    /**
     * Handle operations before applying an update from the server.
     *
     * This can be overridden by views to store state or before cleanup before
     * reloading and re-rendering the HTML from the server.
     *
     * Subclasses do not need to call the parent method.
     *
     * Args:
     *     entryData (object):
     *         The metadata provided by the server in the update.
     */
    beforeApplyUpdate(entryData) {
    },

    /**
     * Handle operations after applying an update from the server.
     *
     * This can be overridden by views to restore state or perform other
     * post-update tasks after reloading and re-rendering the HTML from the
     * server.
     *
     * Subclasses do not need to call the parent method.
     *
     * Args:
     *     entryData (object):
     *         The metadata provided by the server in the update.
     */
    afterApplyUpdate(entryData) {
    },

    /**
     * Handle a click on the expand/collapse button.
     *
     * Toggles the collapsed state of the box.
     */
    _onToggleCollapseClicked() {
        if (this.isCollapsed()) {
            this.expand();
        } else {
            this.collapse();
        }
    },
});
