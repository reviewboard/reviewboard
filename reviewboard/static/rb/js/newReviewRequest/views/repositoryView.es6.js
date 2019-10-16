/**
 * A view representing a single repository.
 */
RB.RepositoryView = Backbone.View.extend({
    tagName: 'li',
    className: 'rb-c-sidebar__nav-item repository',

    template: _.template(dedent`
        <span class="rb-c-sidebar__item-label"><%- name %></span>
    `),

    events: {
        'click': '_onClick',
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.RepositoryView:
     *     This object, for chaining.
     */
    render() {
        this.$el.html(this.template(this.model.attributes));
        this.lowerName = this.model.get('name').toLowerCase();

        return this;
    },

    /**
     * Handler for when this repository is clicked.
     *
     * Emit the 'selected' event.
     */
    _onClick() {
        this.model.trigger('selected', this.model);
    },
});
