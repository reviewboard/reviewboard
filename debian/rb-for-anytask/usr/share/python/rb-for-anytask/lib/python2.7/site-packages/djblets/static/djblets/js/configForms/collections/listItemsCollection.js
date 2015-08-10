/*
 * Base class for a collection of ListItems.
 *
 * This operations just like a standard Backbone.Collection, with two
 * additions:
 *
 * 1) It stored the provided options, for later usage, preventing subclasses
 *    from having to provide their own initialize function.
 *
 * 2) It emits a "fetching" event when calling fetch(), allowing views to
 *    provide a visual indication when items are being fetched or rendered.
 */
Djblets.Config.ListItems = Backbone.Collection.extend({
    initialize: function(models, options) {
        this.options = options;
    },

    /*
     * Fetches the contents of the collection.
     *
     * This will emit the "fetching" event, and then call Backbone.Collection's
     * fetch().
     */
    fetch: function(options) {
        this.trigger('fetching');
        Backbone.Collection.prototype.fetch.call(this, options);
    }
});
