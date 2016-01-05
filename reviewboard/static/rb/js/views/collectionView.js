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
     * Initialize the CollectionView.
     */
    initialize: function(options) {
        var collection = options.collection;

        if (options.itemViewType) {
            this.itemViewType = options.itemViewType;
        }

        this.itemViewOptions = options.itemViewOptions || {};

        this.collection = collection;
        this.views = [];

        collection.each(this._onAdded, this);
        this.listenTo(collection, 'add', this._onAdded);
        this.listenTo(collection, 'remove', this._onRemoved);
        this.listenTo(collection, 'sort', this._onSorted);
        this.listenTo(collection, 'reset', this._onReset);
    },

    /*
     * Render the view.
     *
     * This will iterate over all the child views and render them as well.
     */
    render: function() {
        this._rendered = true;

        this.$el.empty();
        this.views.forEach(function(view) {
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
    _onAdded: function(item) {
        var view;

        console.assert(this.itemViewType,
                       'itemViewType must be defined by the subclass');
        view = new this.itemViewType(_.defaults({
            model: item
        }, this.itemViewOptions));
        this.views.push(view);

        if (this._rendered) {
            this.$el.append(view.render().el);
        }
    },

    /*
     * Remove a view for an item in the collection.
     */
    _onRemoved: function(item) {
        var toRemove = _.find(this.views, function(view) {
            return view.model === item;
        });

        this.views = _.without(this.views, toRemove);
        if (this._rendered) {
            toRemove.remove();
        }
    },

    /*
     * Respond to a change in the collection's sort order.
     *
     * This will detach all of the child views and re-add them in the new
     * order.
     */
    _onSorted: function() {
        var views = this.views;

        this.views = this.collection.map(function(model) {
            var view = _.find(views, function(view) {
                return view.model === model;
            });

            views = _.without(views, view);
            return view;
        });

        if (this._rendered) {
            this.$el.children().detach();
            this.views.forEach(function(view) {
                this.$el.append(view.$el);
            }, this);
        }
    },

    /*
     * Handle the collection being reset.
     *
     * This will remove all existing views and create new ones for the new
     * state of the collection.
     */
    _onReset: function() {
        this.views.forEach(function(view) {
            view.remove();
        });

        this.views = [];
        this.collection.each(this._onAdded, this);
    }
});
