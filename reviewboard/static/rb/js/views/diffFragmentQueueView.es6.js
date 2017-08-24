/**
 * Queues loading of diff fragments from a page.
 *
 * This is used to load diff fragments one-by-one, and to intelligently
 * batch the loads to only fetch at most one set of fragments per file.
 */
RB.DiffFragmentQueueView = Backbone.View.extend({
    /**
     * Initialize the queue.
     *
     * Args:
     *     options (object):
     *         Options passed to this view.
     *
     * Returns:
     *     containerPrefix (string):
     *         The prefix to prepend to diff comment IDs when forming
     *         container element IDs.
     *
     *     reviewRequestPath (string):
     *         The URL for the review request that diff fragments will be
     *         loaded from.
     *
     *     queueName (string):
     *         The name of the diff loading queue.
     */
    initialize(options) {
        this._containerPrefix = options.containerPrefix;
        this._fragmentsBasePath =
            `${options.reviewRequestPath}fragments/diff-comments/`;
        this._queueName = options.queueName;

        this._queue = {};
        this._saved = {};
    },

    /**
     * Queue the load of a diff fragment from the server.
     *
     * This will be added to a list, which will fetch the comments in batches
     * based on file IDs.
     *
     * Args:
     *     commentID (string):
     *         The ID of the comment to queue.
     *
     *     key (string):
     *         The key for the queue. Each comment with the same key will be
     *         loaded in a batch. This will generally be the ID of a file.
     */
    queueLoad(commentID, key) {
        const queue = this._queue;

        if (!queue[key]) {
            queue[key] = [];
        }

        queue[key].push(commentID);
    },

    /**
     * Save a comment's loaded diff fragment for the next load operation.
     *
     * If the comment's diff fragment was already loaded, it will be
     * temporarily stored until the next load operation involving that
     * comment. Instead of loading the fragment from the server, the saved
     * fragment's HTML will be used instead.
     *
     * Args:
     *     commentID (string):
     *         The ID of the comment to save.
     */
    saveFragment(commentID) {
        const $el = this._getCommentContainer(commentID);

        if ($el.length === 1 && $el.data('diff-fragment-view')) {
            this._saved[commentID] = $el.html();
        }
    },

    /**
     * Load all queued diff fragments.
     *
     * The diff fragments for each keyed set in the queue will be loaded as
     * a batch. The resulting fragments will be injected into the DOM.
     *
     * Any existing fragments that were saved will be loaded from the cache
     * without requesting them from the server.
     */
    loadFragments() {
        if (_.isEmpty(this._queue) && _.isEmpty(this._saved)) {
            return;
        }

        const queueName = this._queueName;

        _.each(this._queue, commentIDs => {
            $.funcQueue(queueName).add(() => {
                const pendingCommentIDs = [];

                /*
                 * Check if there are any comment IDs that have been saved.
                 * We don't need to reload these from the server.
                 */
                for (let i = 0; i < commentIDs.length; i++) {
                    const commentID = commentIDs[i];

                    if (this._saved.hasOwnProperty(commentID)) {
                        const view = this._getCommentContainer(commentID)
                            .data('diff-fragment-view');
                        console.assert(view);

                        view.$el.html(this._saved[commentID]);
                        view.render();

                        delete this._saved[commentID];
                    } else {
                        pendingCommentIDs.push(commentID);
                    }
                }

                if (pendingCommentIDs.length > 0) {
                    /*
                     * There are some comment IDs we don't have. Load these
                     * from the server.
                     *
                     * Once these are loaded, they'll call next() on the queue
                     * to process the next batch.
                     */
                    this._loadDiff(pendingCommentIDs.join(','), {
                        queueName: queueName,
                        onDone: () => {
                            _.each(pendingCommentIDs,
                                   this._setupDiffFragmentView,
                                   this);
                        },
                    });
                } else {
                    /*
                     * We processed all we need to process above. Go to the
                     * next queue.
                     */
                    $.funcQueue(queueName).next();
                }
            });
        });

        // Clear the list.
        this._queue = {};

        $.funcQueue(queueName).start();
    },

    /**
     * Return the container for a particular comment.
     *
     * Args:
     *     commentID (string):
     *         The ID of the comment.
     *
     * Returns:
     *     jQuery:
     *     The comment container, wrapped in a jQuery element. The caller
     *     may want to check the length to be sure the container was found.
     */
    _getCommentContainer(commentID) {
        return $(`#${this._containerPrefix}_${commentID}`);
    },

    /**
     * Load a diff fragment for the given comment IDs and options.
     *
     * This will construct the URL for the relevant diff fragment and load
     * it from the server.
     *
     * Args:
     *     commentIDs (string):
     *         A string of comment IDs to load fragments for.
     *
     *     options (object, optional):
     *         Options for the loaded diff fragments.
     *
     * Option Args:
     *     linesOfContext (string):
     *         The lines of context to load for the diff. This is a string
     *         containing a comma-separated set of line counts in the form
     *         of ``numLinesBefore,numLinesAfter``.
     *
     *     onDone (function):
     *         A function to call after the diff has been loaded.
     *
     *     queueName (string):
     *         The name of the load queue. This is used to load batches of
     *         fragments sequentially.
     */
    _loadDiff(commentIDs, options={}) {
        const queryArgs = [
            `container_prefix=${this._containerPrefix}`,
        ];

        if (options.queueName !== undefined) {
            queryArgs.push(`queue=${options.queueName}`);
        }

        if (options.linesOfContext !== undefined) {
            queryArgs.push(`lines_of_context=${options.linesOfContext}`);
        }

        queryArgs.push(TEMPLATE_SERIAL);

        this._addScript(
            `${this._fragmentsBasePath}${commentIDs}/?${queryArgs.join('&')}`,
            options.onDone);
    },

    /*
     * Add a script tag to the page and set up a callback handler for load.
     *
     * The browser will load the script at the specified URL, execute it, and
     * call a handler when the load has finished. It's expected this will be
     * called after the page is already otherwise loaded.
     *
     * Args:
     *     url (string):
     *         The URL of the script to load.
     *
     *     callback (function, optional):
     *         An optional callback function to call once the script has
     *         loaded.
     */
    _addScript(url, callback) {
        const e = document.createElement('script');

        e.type = 'text/javascript';
        e.src = url;

        if (callback !== undefined) {
            e.addEventListener('load', callback);
        }

        document.body.appendChild(e);
    },

    /**
     * Set up state for a fragment when it's first loaded.
     *
     * When a comment container loads its contents for the first time, the
     * controls will be hidden and the hover-related events will be registered
     * to allow the fragment to be expanded/collapsed.
     *
     * Args:
     *     commentID (string):
     *         The ID of the comment used to build the container ID.
     */
    _setupDiffFragmentView(commentID) {
        const view = new RB.DiffFragmentView({
            el: this._getCommentContainer(commentID),
            loadDiff: options => {
                RB.setActivityIndicator(true, {type: 'GET'});

                this._loadDiff(commentID, _.defaults({
                    onDone() {
                        RB.setActivityIndicator(false, {});

                        if (options.onDone) {
                            options.onDone();
                        }
                    },
                }, options));
            },
        });
        view.render().$el
            .data('diff-fragment-view', view);
    },
});
