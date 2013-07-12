/*
 * A view for a single branch.
 *
 * This is presented as an <option> within a <select>
 */
RB.BranchView = Backbone.View.extend({
    tagName: 'option',

    /*
     * Render the view.
     */
    render: function() {
        this.$el
            .text(this.model.get('name'))
            .attr('selected', this.model.get('isDefault'));

        return this;
    }
});
