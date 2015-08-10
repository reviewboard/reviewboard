/*
 * Copyright 2008-2010 Christian Hammond.
 * Copyright 2010-2013 Beanbag, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to
 * deal in the Software without restriction, including without limitation the
 * rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
 * sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */
(function($) {


var queues = {},
    queuesInProgress = {};

/*
 * A set of utility functions for implementing a queue of functions.
 * Functions are added to the queue and, when their operation is complete,
 * they are to call next(), which will trigger the next function in the
 * queue.
 *
 * There can be multiple simultaneous queues going at once. They're identified
 * by queue names that are passed to funcQueue().
 */
$.funcQueue = function(name) {
    var self = this;

    if (!queues[name]) {
        queues[name] = [];
    }

    /*
     * Adds a function to the queue.
     *
     * This will just add the item to the queue. To start the queue, run
     * start() after adding the function.
     *
     * @param {function} func    The function to add.
     * @param {object}   context The context in which to invoke the function.
     */
    this.add = function(func, context) {
        if (func) {
            queues[name].push([func, context]);
        }
    };

    /*
     * Invokes the next function in the queue.
     *
     * This should only be called when a task in the queue is finished.
     * Calling this function will immediately process the next item in the
     * queue, out of order.
     *
     * Callers wanting to ensure the queue is running after adding the
     * initial item should call start() instead.
     */
    this.next = function() {
        var info,
            func,
            context;

        if (queuesInProgress[name]) {
            info = queues[name].shift();

            if (info) {
                func = info[0];
                context = info[1];

                func.call(context);
            } else {
                queuesInProgress[name] = false;
            }
        }
    };

    /*
     * Begins the queue.
     *
     * If a queue has already been started, this will do nothing.
     */
    this.start = function() {
        if (!queuesInProgress[name] && queues[name].length > 0) {
            queuesInProgress[name] = true;
            self.next();
        }
    };

    /*
     * Clears the queue, removing all pending functions.
     */
    this.clear = function() {
        queues[name] = [];
        queuesInProgress[name] = false;
    };

    return this;
};


})(jQuery);

// vim: set et:
