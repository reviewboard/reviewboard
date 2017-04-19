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


/**
 * Return a function that will be called when the call stack has unwound.
 *
 * This will return a function that calls the provided function using
 * :js:func:`_.defer`.
 *
 * Args:
 *     func (function):
 *         The function to call.
 *
 * Returns:
 *     function:
 *     The wrapper function.
 */
_.deferred = function(func) {
    return () => {
        _.defer(func);
    };
};


/**
 * Return a function suitable for efficiently handling page layout.
 *
 * The returned function will use :js:func:`window.requestAnimationFrame` to
 * schedule the layout call. Once this function called, any subsequent calls
 * will be ignored until the first call has finished the layout work.
 *
 * Optionally, this can also defer layout work until the call stack has unwound.
 *
 * This is intended to be used as a resize event handler.
 *
 * Args:
 *     layoutFunc (function):
 *         The function to call to perform layout.
 *
 *     options (object):
 *         Options for the layout callback.
 *
 * Option Args:
 *     defer (boolean):
 *         If ``true``, the layout function will be called when the call stack
 *         has unwound after the next scheduled layout call.
 */
_.throttleLayout = function(layoutFunc, options={}) {
    let handlingLayout = false;

    /*
     * We don't want to use a fat arrow function here, since we need the
     * caller's context to be preserved.
     */
    return function() {
        if (handlingLayout) {
            return;
        }

        const context = this;
        const args = arguments;

        handlingLayout = true;

        let cb = () => {
            layoutFunc.apply(context, args);
            handlingLayout = false;
        };

        if (options.defer) {
            cb = _.deferred(cb);
        }

        requestAnimationFrame(cb);
    };
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
