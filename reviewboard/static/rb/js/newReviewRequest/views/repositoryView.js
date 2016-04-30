/*
 * A view representing a single repository.
 */
RB.RepositoryView = Backbone.View.extend({
    tagName: 'li',
    className: 'has-url item repository',

    template: _.template([
        '<div class="page-sidebar-row">',
        '<span class="label"><%- name %></span>',
        '</div>'
    ].join('')),

    events: {
        'click': '_onClick'
    },

    /*
     * Render the view.
     */
    render: function() {
        this.$el.html(this.template(this.model.attributes));
        this.lowerName = this.model.get('name').toLowerCase();
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
