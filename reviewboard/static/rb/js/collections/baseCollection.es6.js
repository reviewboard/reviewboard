/**
 * The base class used for Review Board collections.
 *
 * This is a thin subclass over Backbone.Collection that just provides
 * some useful additional abilities.
 */
RB.BaseCollection = Backbone.Collection.extend({
    /**
     * Fetch models from the server.
     *
     * This behaves just like Backbone.Collection.fetch, except it
     * takes a context parameter for callbacks.
     *
     * Args:
     *     options (object):
     *         Options for the fetch operation.
     *
     *     context (object):
     *         Context to be used when calling success/error/complete
     *         callbacks.
     */
    fetch(options={}, context=undefined) {
        options = _.bindCallbacks(options, context);

        return Backbone.Collection.prototype.fetch.call(this, options);
    },

    /**
     * Handle all AJAX communication for the collection.
     *
     * Backbone.js will internally call the model's sync function to
     * communicate with the server, which usually uses Backbone.sync.
     *
     * This will parse error response from Review Board so we can provide
     * a more meaningful error callback.
     *
     * Args:
     *     method (string):
     *         The HTTP method to use for the AJAX request.
     *
     *     model (object):
     *         The model to sync.
     *
     *     options (object):
     *         Options for the sync operation.
     */
    sync(method, model, options={}) {
        return Backbone.sync.call(this, method, model, _.defaults({
            error: xhr => {
                RB.storeAPIError(xhr);

                if (_.isFunction(options.error)) {
                    options.error(xhr);
                }
            }
        }, options));
    }
});
