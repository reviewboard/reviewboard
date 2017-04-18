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
    return function() {
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
_.throttleLayout = function(layoutFunc, options) {
    var handlingLayout = false;

    options = options || {};

    return function() {
        var context = this,
            args = arguments,
            cb;

        if (handlingLayout) {
            return;
        }

        handlingLayout = true;

        cb = function() {
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
 * Returns the parent prototype for an object.
 */
_super = function(obj) {
    return Object.getPrototypeOf(Object.getPrototypeOf(obj));
};
