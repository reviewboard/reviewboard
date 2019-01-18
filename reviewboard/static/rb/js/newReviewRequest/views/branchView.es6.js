/**
 * A view for a single branch.
 *
 * This is presented as an ``<option>`` within a ``<select>``.
 */
RB.BranchView = Backbone.View.extend({
    tagName: 'option',

    /**
     * Render the view.
     *
     * Returns:
     *     RB.BranchView:
     *     This object, for chaining.
     */
    render() {
        this.$el
            .text(this.model.get('name'))
            .attr('selected', this.model.get('isDefault'));

        return this;
    },
});
