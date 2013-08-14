/*
 * A view for selecting a repository from a collection.
 */
RB.RepositorySelectionView = RB.CollectionView.extend({
    className: 'repository-selector',
    itemViewType: RB.RepositoryView,

    /*
     * Initialize the view.
     */
    initialize: function() {
        _.super(this).initialize.apply(this, arguments);

        this._selected = null;

        this.listenTo(this.collection, 'selected', this._onRepositorySelected);
    },

    /*
     * Render the view.
     */
    render: function() {
        _.super(this).render.apply(this, arguments);

        $('<h3>').text(gettext('Repositories')).prependTo(this.$el);
        return this;
    },

    /*
     * Callback for when an individual repository is selected.
     *
     * Ensures that the selected repository has the 'selected' class applied
     * (and no others do), and triggers the 'selected' event on the view.
     */
    _onRepositorySelected: function(item) {
        this._selected = item;

        _.each(this.views, function(view) {
            if (view.model === item) {
                view.$el.addClass('selected');
            } else {
                view.$el.removeClass('selected');
            }
        });

        this.trigger('selected', item);
    }
});
