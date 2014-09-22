/*
 * The base class used for Review Board collections.
 *
 * This is a thin subclass over Backbone.Collection that just provides
 * some useful additional abilities.
 */
RB.BaseCollection = Backbone.Collection.extend({
    /*
     * Fetches models from the server.
     *
     * This behaves just like Backbone.Collection.fetch, except it
     * takes a context parameter for callbacks.
     */
    fetch: function(options, context) {
        options = _.bindCallbacks(options || {}, context);

        return Backbone.Collection.prototype.fetch.call(this, options);
    },

    /*
     * Handles all AJAX communication for the collection.
     *
     * Backbone.js will internally call the model's sync function to
     * communicate with the server, which usually uses Backbone.sync.
     *
     * This will parse error response from Review Board so we can provide
     * a more meaningful error callback.
     */
    sync: function(method, model, options) {
        options = options || {};

        return Backbone.sync.call(this, method, model, _.defaults({
            error: _.bind(function(xhr) {
                RB.storeAPIError(xhr);

                if (_.isFunction(options.error)) {
                    options.error(xhr);
                }
            }, this)
        }, options));
    }
});
