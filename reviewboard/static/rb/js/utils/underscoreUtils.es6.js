/**
 * Bind callbacks to a context.
 *
 * Backbone.js's various ajax-related functions don't take a context
 * with their callbacks. This allows us to wrap these callbacks to ensure
 * we always have a desired context.
 *
 * Args:
 *     callbacks (object):
 *         An object which potentially includes callback functions.
 *
 *     context (any type):
 *         The context to bind to the callbacks.
 *
 *     methodNames (Array of string):
 *         An array of method names within ``callbacks`` to bind.
 *
 * Returns:
 *     object:
 *     A copy of the ``callbacks`` object, with the given ``methodNames`` bound
 *     to ``context``.
 */
_.bindCallbacks = function(callbacks, context,
                           methodNames=['success', 'error', 'complete']) {
    if (!context) {
        return callbacks;
    }

    const wrappedCallbacks = {};

    for (let [key, value] of Object.entries(callbacks)) {
        if (methodNames.includes(key) && _.isFunction(value)) {
            wrappedCallbacks[key] = _.bind(value, context);
        }
    }

    return _.defaults(wrappedCallbacks, callbacks);
};


/*
 * Return the parent prototype for an object.
 *
 * Args:
 *     obj (object):
 *         An object.
 *
 * Returns:
 *     object:
 *     The object which is the parent prototype for the given ``obj``. This is
 *     roughly equivalent to what you'd get from ES6's ``super``.
 */
window._super = function(obj) {
    return Object.getPrototypeOf(Object.getPrototypeOf(obj));
};
