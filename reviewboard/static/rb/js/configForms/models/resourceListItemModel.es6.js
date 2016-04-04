/**
 * A list item representing a resource in the API.
 *
 * This item will be backed by a resource model, which will be used for
 * all synchronization with the API. It will work as a proxy for requests
 * and events, and synchronize attributes between the resource and the list
 * item. This allows callers to work directly with the list item instead of
 * digging down into the resource.
 */
RB.Config.ResourceListItem = Djblets.Config.ListItem.extend({
    defaults: _.defaults({
        resource: null
    }, Djblets.Config.ListItem.prototype.defaults),

    /** A list of attributes synced between the ListItem and the Resource. */
    syncAttrs: [],

    /**
     * Initialize the list item.
     *
     * This will begin listening for events on the resource, updating
     * the state of the icon based on changes.
     */
    initialize() {
        let resource = this.get('resource');

        if (resource) {
            this.set(_.pick(resource.attributes, this.syncAttrs));
        } else {
            /*
             * Create a resource using the attributes provided to this list
             * item.
             */
            resource = this.createResource(_.extend(
                { id: this.get('id') },
                _.pick(this.attributes, this.syncAttrs)));

            this.set('resource', resource);
        }

        this.resource = resource;

        Djblets.Config.ListItem.prototype.initialize.apply(this, arguments);

        /* Forward on a couple events we want the caller to see. */
        this.listenTo(resource, 'request',
                      (...args) => this.trigger('request', ...args));
        this.listenTo(resource, 'sync',
                      (...args) => this.trigger('sync', ...args));

        /* Destroy this item when the resource is destroyed. */
        this.listenTo(resource, 'destroy', this.destroy);

        /*
         * Listen for each synced attribute change so we can update this
         * list item.
         */
        this.syncAttrs.forEach(
            attr => this.listenTo(resource, `change:${attr}`,
                                  (model, value) => this.set(attr, value)));
    },

    /**
     * Create the Resource for this list item, with the given attributes.
     */
    createResource(/* attrs */) {
        console.assert(false, 'createResource must be implemented');
    },

    /**
     * Destroy the list item.
     *
     * This will just emit the 'destroy' signal. It is typically called when
     * the resource itself is destroyed.
     *
     * Args:
     *     options (object):
     *         Options for the destroy operation.
     *
     * Option Args:
     *     success (function):
     *         Optional success callback.
     */
    destroy(options={}) {
        this.stopListening(this.resource);
        this.trigger('destroy', this, this.collection, options);

        if (_.isFunction(options.success)) {
            options.success(this, null, options);
        }
    }
});
