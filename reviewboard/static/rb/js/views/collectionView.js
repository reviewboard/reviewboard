/*
 * An abstract view for rendering a collection.
 *
 * This provides core, reusable functionality for any view that wants to render
 * a collection and respond to add/remove events. Types that extend this should
 * make sure to define the 'itemViewType' attribute, which will be the view
 * instantiated for each model in the collection.
 */
RB.CollectionView = Backbone.View.extend({
    /*
     * The view that will be instantiated for rendering items in the collection.
     */
    itemViewType: null,

    /*
     * Initializes CollectionView.
     */
    initialize: function(options) {
        var collection = options.collection;

        this.collection = collection;
        this.views = [];

        collection.each(this._add, this);
        collection.on({
            add: this._add,
            remove: this._remove
        }, this);
    },

    /*
     * Renders the view.
     *
     * This will iterate over all the child views and render them as well.
     */
    render: function() {
        this._rendered = true;

        this.$el.empty();
        _.each(this.views, function(view) {
            this.$el.append(view.render().el);
        }, this);

        return this;
    },

    /*
     * Add a view for an item in the collection.
     *
     * This will instantiate the itemViewType, and if the CollectionView has
     * been rendered, render and append it as well.
     */
    _add: function(item) {
        var view;

        console.assert(this.itemViewType,
                       'itemViewType must be defined by the subclass');
        view = new this.itemViewType({
            model: item
        });
        this.views.push(view);

        if (this._rendered) {
            this.$el.append(view.render().el);
        }
    },

    /*
     * Remove a view for an item in the collection.
     */
    _remove: function(item) {
        var grouped = _.groupBy(this.views, function(view) {
            return view.model === item ? 'toRemove' : 'toKeep';
        });

        this.views = grouped.toKeep || [];

        if (this._rendered) {
            _.each(grouped.toRemove, function(view) {
                view.remove();
            });
        }
    }
});
