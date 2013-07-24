/*
 * A view representing a single repository.
 */
RB.RepositoryView = Backbone.View.extend({
    className: 'repository',

    template: _.template([
        '<div><%- name %></div>'
    ].join('')),

    events: {
        'click': '_onClick'
    },

    /*
     * Render the view.
     */
    render: function() {
        this.$el.html(this.template(this.model.attributes));
        return this;
    },

    /*
     * Handler for when this repository is clicked.
     *
     * Emit the 'selected' event.
     */
    _onClick: function() {
        this.model.trigger('selected', this.model);
    }
});
