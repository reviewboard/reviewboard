/*
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

    /* A list of attributes synced between the ListItem and the Resource. */
    syncAttrs: [],

    /*
     * Initializes the list item.
     *
     * This will begin listening for events on the resource, updating
     * the state of the icon based on changes.
     */
    initialize: function(options) {
        var resource = this.get('resource');

        if (resource) {
            this.set(_.pick(resource.attributes, this.syncAttrs));
        } else {
            /*
             * Create a resource using the attributes provided to this list
             * item.
             */
            resource = this.createResource(_.extend(
                {
                    id: this.get('id')
                },
                _.pick(this.attributes, this.syncAttrs)));

            this.set('resource', resource);
        }

        this.resource = resource;

        Djblets.Config.ListItem.prototype.initialize.call(this, options);

        /* Forward on a couple events we want the caller to see. */
        this.listenTo(resource, 'request', function() {
            this.trigger('request');
        });

        this.listenTo(resource, 'sync', function() {
            this.trigger('sync');
        });

        /* Destroy this item when the resource is destroyed. */
        this.listenTo(resource, 'destroy', this.destroy);

        /*
         * Listen for each synced attribute change so we can update this
         * list item.
         */
        _.each(this.syncAttrs, function(attr) {
            this.listenTo(resource, 'change:' + attr, function(model, value) {
                this.set(attr, value);
            });
        }, this);
    },

    /*
     * Creates the Resource for this list item, with the given attributes.
     */
    createResource: function(/* attrs */) {
        console.assert(false, 'createResource must be implemented');
    },

    /*
     * Destroys the list item.
     *
     * This will just emit the 'destroy' signal. It is typically called when
     * the resource itself is destroyed.
     */
    destroy: function(options) {
        this.stopListening(this.resource);
        this.trigger('destroy', this, this.collection, options);

        if (options && options.success) {
            options.success(this, null, options);
        }
    }
});
