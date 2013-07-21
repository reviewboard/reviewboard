/*
 * Represents a box on the page that can be collapsed.
 */
RB.CollapsableBoxView = Backbone.View.extend({
    events: {
        'click .collapse-button': '_onToggleCollapseClicked'
    },

    /*
     * Renders the box.
     */
    render: function() {
        this._$box = this.$('.box');
        this._$expandCollapseButton = this.$('.collapse-button .rb-icon');

        if (this._$box.hasClass('collapsed')) {
            this._$expandCollapseButton.addClass('rb-icon-expand-review');
        } else {
            this._$expandCollapseButton.addClass('rb-icon-collapse-review');
        }

        return this;
    },

    /*
     * Expands the box.
     */
    expand: function() {
        this._$box.removeClass('collapsed');
        this._$expandCollapseButton
            .removeClass('rb-icon-expand-review')
            .addClass('rb-icon-collapse-review');
    },

    /*
     * Collapses the box.
     */
    collapse: function() {
        this._$box.addClass('collapsed');
        this._$expandCollapseButton
            .removeClass('rb-icon-collapse-review')
            .addClass('rb-icon-expand-review');
    },

    /*
     * Handler for when the Expand/Collapse button is clicked.
     *
     * Toggles the collapsed state of the box.
     */
    _onToggleCollapseClicked: function() {
        if (this._$box.hasClass('collapsed')) {
            this.expand();
        } else {
            this.collapse();
        }
    }
});


