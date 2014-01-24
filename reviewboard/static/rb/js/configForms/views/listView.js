/*
 * Displays a list of items.
 *
 * This will render each item in a list, and update that list when the
 * items in the collection changes.
 *
 * It can also filter the displayed list of items.
 *
 * If loading the list through the API, this will display a loading indicator
 * until the items have been loaded.
 */
RB.Config.ListView = Backbone.View.extend({
    tagName: 'ul',
    className: 'config-forms-list',

    /*
     * Initializes the view.
     */
    initialize: function(options) {
        var collection = this.model.collection;

        this.ItemView = options.ItemView || RB.Config.ListItemView;

        this.listenTo(collection, 'add', this._addItem);
        this.listenTo(collection, 'remove', this._removeItem);
        this.listenTo(collection, 'reset', this.render);
    },

    /*
     * Returns the body element.
     *
     * This can be overridden by subclasses if the list items should be
     * rendered to a child element of this view.
     */
    getBody: function() {
        return this.$el;
    },

    /*
     * Renders the list of items.
     *
     * This will loop through all items and render each one.
     */
    render: function() {
        this.$listBody = this.getBody().empty();
        this.model.collection.each(this._addItem, this);

        return this;
    },

    /*
     * Creates a view for an item and adds it.
     */
    _addItem: function(item) {
        var view = new this.ItemView({
            model: item
        });

        this.$listBody.append(view.render().$el);
    },

    /*
     * Handler for when an item is removed from the collection.
     *
     * Removes the element from the list.
     */
    _removeItem: function(item, collection, options) {
        this.$listBody.children().eq(options.index).remove();
    }
});
