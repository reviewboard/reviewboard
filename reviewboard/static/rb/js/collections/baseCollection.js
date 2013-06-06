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
    }
});
