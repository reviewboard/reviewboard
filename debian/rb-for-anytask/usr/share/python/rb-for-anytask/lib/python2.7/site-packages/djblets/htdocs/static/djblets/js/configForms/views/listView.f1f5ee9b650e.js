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
 *
 * If 'options.animateItems' is true, then newly added or removed items will
 * be faded in/out.
 */
Djblets.Config.ListView = Backbone.View.extend({
    tagName: 'ul',
    className: 'config-forms-list',
    defaultItemView: Djblets.Config.ListItemView,

    /*
     * Initializes the view.
     */
    initialize: function(options) {
        var collection = this.model.collection;

        options = options || {};

        this.ItemView = options.ItemView || this.defaultItemView;
        this.animateItems = !!options.animateItems;

        this.once('rendered', function() {
            this.listenTo(collection, 'add', this._addItem);
            this.listenTo(collection, 'remove', this._removeItem);
            this.listenTo(collection, 'reset', this._renderItems);
        }, this);
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
        this.$listBody = this.getBody();

        this._renderItems();
        this.trigger('rendered');

        return this;
    },

    /*
     * Creates a view for an item and adds it.
     */
    _addItem: function(item, collection, options) {
        var view = new this.ItemView({
                model: item
            }),
            animateItem = (options && options.animate !== false);

        view.render();

        /*
         * If this ListView has animation enabled, and this specific
         * item is being animated (the default unless options.animate
         * is false), we'll fade in the item.
         */
        if (this.animateItems && animateItem) {
            view.$el.fadeIn();
        }

        this.$listBody.append(view.$el);
    },

    /*
     * Handler for when an item is removed from the collection.
     *
     * Removes the element from the list.
     */
    _removeItem: function(item, collection, options) {
        var $item = this.$listBody.children().eq(options.index),
            animateItem = (options && options.animate !== false);

        /*
         * If this ListView has animation enabled, and this specific
         * item is being animated (the default unless options.animate
         * is false), we'll fade out the item.
         */
        if (this.animateItems && animateItem) {
            $item.fadeOut(function() {
                $item.remove();
            });
        } else {
            $item.remove();
        }
    },

    /*
     * Renders all items from the list.
     */
    _renderItems: function() {
        this.$listBody.empty();

        this.model.collection.each(function(item) {
            this._addItem(item, item.collection, {
                animate: false
            });
        }, this);
    }
});
