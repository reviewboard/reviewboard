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
     * Expand the box.
     */
    expand() {
        this._$box.removeClass('collapsed');
        this._$expandCollapseButton
            .removeClass('rb-icon-expand-review')
            .addClass('rb-icon-collapse-review');
    },

    /**
     * Collapse the box.
     */
    collapse() {
        this._$box.addClass('collapsed');
        this._$expandCollapseButton
            .removeClass('rb-icon-collapse-review')
            .addClass('rb-icon-expand-review');
    },

    /**
     * Handle a click on the expand/collapse button.
     *
     * Toggles the collapsed state of the box.
     */
    _onToggleCollapseClicked() {
        if (this._$box.hasClass('collapsed')) {
            this.expand();
        } else {
            this.collapse();
        }
    },
});
