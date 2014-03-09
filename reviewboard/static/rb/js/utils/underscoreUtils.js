var DEFAULT_WRAPPED_CALLBACKS = ['success', 'error', 'complete'];


/*
 * Binds callbacks with a bound context.
 *
 * Backbone.js's various ajax-related functions don't take a context
 * with their callbacks. This allows us to wrap these callbacks to ensure
 * we always have a desired context.
 */
_.bindCallbacks = function(callbacks, context, methodNames) {
    var wrappedCallbacks;

    if (!context) {
        return callbacks;
    }

    if (!methodNames) {
        methodNames = DEFAULT_WRAPPED_CALLBACKS;
    }

    wrappedCallbacks = {};

    _.each(callbacks, function(value, key) {
        wrappedCallbacks[key] = _.isFunction(callbacks[key])
                                ? _.bind(callbacks[key], context)
                                : undefined;
    });

    return _.defaults(wrappedCallbacks, callbacks);
};


/*
 * Returns the parent prototype for an object.
 */
_super = function(obj) {
    return Object.getPrototypeOf(Object.getPrototypeOf(obj));
};
