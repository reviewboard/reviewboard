/*
 * A collection for filtered results from another collection.
 *
 * This allows a consumer to filter the contents of another collection.
 * A filter can be set by passing the 'filters' option at construction
 * time or calling setFilters, both taking a dictionary of attributes and
 * values. In order for an item to be in this collection, each key in the item
 * must start with the value in the filter.
 */
RB.FilteredCollection = RB.BaseCollection.extend({
    /*
     * Initializes the collection.
     *
     * This begins listening for events on the main collection, in order
     * to update and present a filtered view.
     */
    initialize: function(models, options) {
        this.collection = options.collection;
        this.filters = options.filters;

        this.listenTo(this.collection, 'add', this._onItemAdded);
        this.listenTo(this.collection, 'remove', this.remove);
        this.listenTo(this.collection, 'reset', this._rebuild);

        this._rebuild();
    },

    /*
     * Sets new filters for the collection.
     *
     * The items in the collection will be rebuilt to match the filter.
     */
    setFilters: function(filters) {
        this.filters = filters;

        this._rebuild();
    },

    /*
     * Handler for when an item in the main collection is added.
     *
     * If the item passes the filter, it will be added to this collection
     * as well.
     */
    _onItemAdded: function(item) {
        if (this._passesFilters(item, true)) {
            this.add(item);
        }
    },

    /*
     * Rebuilds the collection.
     *
     * This iterates through all the items in the main collection and
     * adds any that pass the filter to this collection.
     */
    _rebuild: function() {
        if (_.isEmpty(this.filters)) {
            this.reset(this.collection.models);
        } else {
            this.reset(this.collection.filter(this._passesFilters, this));
        }
    },

    /*
     * Returns whether an item passes the filters.
     */
    _passesFilters: function(item, checkEmpty) {
        if (checkEmpty && (!this.filters || _.isEmpty(this.filters))) {
            return true;
        }

        return _.every(this.filters, function(value, key) {
            var attrValue = item.get(key);

            if (_.isString(value)) {
                return attrValue.indexOf(value) === 0;
            } else {
                return attrValue === value;
            }
        });
    }
});
