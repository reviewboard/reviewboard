/**
 * A collection for filtered results from another collection.
 *
 * This allows a consumer to filter the contents of another collection.
 * A filter can be set by passing the 'filters' option at construction
 * time or calling setFilters, both taking a dictionary of attributes and
 * values. In order for an item to be in this collection, each key in the item
 * must start with the value in the filter.
 */
RB.FilteredCollection = RB.BaseCollection.extend({
    /**
     * Initialize the collection.
     *
     * This begins listening for events on the main collection, in order
     * to update and present a filtered view.
     *
     * Args:
     *     models (Array of object):
     *         Initial models for the collection.
     *
     *     options (object):
     *         Options for the collection.
     *
     * Option Args:
     *     collection (Backbone.Collection):
     *         Main collection to filter.
     *
     *     filters (object):
     *         A set of filters to apply. This is an object where the keys are
     *         the name of the attributes and the values are the value to
     *         filter for. If the values are strings, this will do a
     *         starts-with comparison.
     */
    initialize(models, options) {
        this.collection = options.collection;
        this.filters = options.filters;

        this.listenTo(this.collection, 'add', this._onItemAdded);
        this.listenTo(this.collection, 'remove', this.remove);
        this.listenTo(this.collection, 'reset', this._rebuild);

        this._rebuild();
    },

    /**
     * Set new filters for the collection.
     *
     * The items in the collection will be rebuilt to match the filter.
     *
     * Args:
     *     filters (object):
     *         A list of filters to apply.
     */
    setFilters(filters) {
        this.filters = filters;

        this._rebuild();
    },

    /**
     * Handler for when an item in the main collection is added.
     *
     * If the item passes the filter, it will be added to this collection
     * as well.
     *
     * Args:
     *     item (Backbone.Model):
     *         The newly-added item.
     */
    _onItemAdded(item) {
        if (this._passesFilters(item, true)) {
            this.add(item);
        }
    },

    /**
     * Rebuild the collection.
     *
     * This iterates through all the items in the main collection and
     * adds any that pass the filter to this collection.
     */
    _rebuild() {
        if (_.isEmpty(this.filters)) {
            this.reset(this.collection.models);
        } else {
            this.reset(this.collection.filter(this._passesFilters, this));
        }
    },

    /**
     * Return whether an item passes the filters.
     *
     * Args:
     *     item (Backbone.Model):
     *         The item to check.
     *
     *     checkEmpty (boolean):
     *         Whether to allow items if the filters list is empty.
     */
    _passesFilters(item, checkEmpty) {
        if (checkEmpty && (!this.filters || _.isEmpty(this.filters))) {
            return true;
        }

        return _.every(this.filters, (value, key) => {
            const attrValue = item.get(key);

            if (_.isString(value)) {
                return attrValue.indexOf(value) === 0;
            } else {
                return attrValue === value;
            }
        });
    }
});
