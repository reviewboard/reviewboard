/*
 * Queues loading of diff fragments from a page.
 *
 * This is used to load diff fragments one-by-one, and to intelligently
 * batch the loads to only fetch at most one set of fragments per file.
 */
RB.DiffFragmentQueueView = Backbone.View.extend({
    initialize: function() {
        this._queue = {};
    },

    /*
     * Queues the load of a diff fragment from the server.
     *
     * This will be added to a list, which will fetch the comments in batches
     * based on file IDs.
     */
    queueLoad: function(comment_id, key) {
        var queue = this._queue;

        if (!queue[key]) {
            queue[key] = [];
        }

        queue[key].push(comment_id);
    },

    /*
     * Begins the loading of all diff fragments on the page belonging to
     * the specified queue.
     */
    loadFragments: function() {
        var queueName = this.options.queueName,
            urlPrefix,
            urlSuffix;

        if (!this._queue) {
            return;
        }

        urlPrefix = this.options.reviewRequestPath +
                    'fragments/diff-comments/';
        urlSuffix = '/?queue=' + queueName +
                    '&container_prefix=' + this.options.containerPrefix +
                    '&' + TEMPLATE_SERIAL;

        _.each(this._queue, function(comments) {
            var url = urlPrefix + comments.join(',') + urlSuffix;

            $.funcQueue(queueName).add(_.bind(function() {
                this._addScript(url);
            }, this));
        }, this);

        // Clear the list.
        this._queue = {};

        $.funcQueue(queueName).start();
    },

    /*
     * Adds a script tag for a diff fragment to the bottom of the page.
     */
    _addScript: function(url) {
        var e = document.createElement('script');

        e.type = 'text/javascript';
        e.src = url;
        document.body.appendChild(e);
    }
});
