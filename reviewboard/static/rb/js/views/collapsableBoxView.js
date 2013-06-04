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

        return this;
    },

    /*
     * Expands the box.
     */
    expand: function() {
        this._$box.removeClass('collapsed');
    },

    /*
     * Collapses the box.
     */
    collapse: function() {
        this._$box.addClass('collapsed');
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


