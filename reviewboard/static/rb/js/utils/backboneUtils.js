/*
 * Binds a callback to an event just once.
 *
 * The callback will be disconnected as soon as it fires.
 */
var once = function(evt, callback, context) {
    var cb = _.bind(function() {
        this.off(evt, cb);
        callback.apply(context || this, arguments);
    }, this);

    this.on(evt, cb);
};

Backbone.Events.once = once;
Backbone.Model.prototype.once = once;
Backbone.Collection.prototype.once = once;
Backbone.View.prototype.once = once;
