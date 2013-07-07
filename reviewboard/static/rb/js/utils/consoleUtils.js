var _origAssert;

if (typeof window.console === 'undefined') {
    window.console = {};
}

_origAssert = console.assert;

if (typeof console.log === 'undefined') {
    console.log = function() {};
}

if (typeof console.warn === 'undefined') {
    console.warn = function() {};
}

if (typeof console.error === 'undefined') {
    console.error = function() {};
}

/*
 * console.assert may not behave as we'd hope on all implementations.
 * On Chrome, for instance, it doesn't raise an exception. So, fall back
 * to raising one.
 */
console.assert = function(conditional, msg) {
    if (_origAssert && _origAssert.call) {
        _origAssert.call(console, conditional, msg);
    }

    /* If the above assert never raised an exception, raise our own. */
    if (!conditional) {
        throw new Error(msg);
    }
};
