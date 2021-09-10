/**
 * A collection of commits in a repository.
 *
 * This is expected to be used in an ephemeral manner to get a list of commits
 * from a given start point (usually corresponding to some branch in the
 * repository).
 */
RB.RepositoryCommits = RB.BaseCollection.extend({
    model: RB.RepositoryCommit,

    /**
     * Initialize the collection.
     *
     * Args:
     *     models (Array of object):
     *         Initial models for the collection.
     *
     *     options (Object):
     *         Options for the collection.
     *
     * Option Args:
     *     start (string):
     *         The start commit for fetching commit logs.
     *
     *     branch (string):
     *         The branch name for fetching commit logs.
     *
     *     urlBase (string):
     *         The base URL for the API request.
     */
    initialize(models, options) {
        Backbone.Collection.prototype.initialize.call(this, models, options);
        this.options = options;
        this.busy = false;
        this.complete = false;
        this._nextStart = null;
    },

    /**
     * Parse the response.
     *
     * Args:
     *     response (object):
     *         Response, parsed from the JSON returned by the server.
     *
     * Returns:
     *     Array of object:
     *     An array of commits.
     */
    parse(response) {
        const commits = response.commits;

        this._nextStart = commits[commits.length - 1].parent;
        this.complete = !this._nextStart;

        return response.commits;
    },

    /**
     * Get the URL to fetch for the next page of results.
     *
     * Returns:
     *     string:
     *     The URL to fetch.
     */
    url() {
        const params = {};

        if (this.options.start !== undefined) {
            params.start = this.options.start;
        }

        if (this.options.branch !== undefined) {
            params.branch = this.options.branch;
        }

        return this.options.urlBase + '?' + $.param(params);
    },

    /**
     * Return whether another page of commits can be fetched.
     *
     * A page can only be fetched if there's at least 1 commit already
     * fetched, the last commit in the repository has not been fetched, and
     * another fetch operation isn't in progress.
     *
     * Version Added:
     *     4.0.3
     *
     * Returns:
     *     boolean:
     *     ``true`` if another page can be fetched. ``false`` if one cannot.
     */
    canFetchNext() {
        return !this.busy && !this.complete && this.models.length > 0;
    },

    /**
     * Fetch the next page of results.
     *
     * This can be called multiple times. If this is called when a fetch is
     * already in progress, it's a no-op. Otherwise, if there are more commits
     * to load, it will fetch them and add them to the bottom of the
     * collection.
     *
     * It's up to the caller to check :js:func:`canFetchNext()` before calling
     * this if they want callbacks to fire.
     *
     * Version Changed:
     *     4.0.3:
     *     Added the ``options`` argument with ``error`` and ``success``
     *     callbacks.
     *
     * Version Changed:
     *     5.0:
     *     Added the promise return value.
     *
     * Args:
     *     options (object, optional):
     *         Options for fetching the next page of results.
     *
     *     context (object, optional):
     *         Context to use when calling callbacks.
     *
     * Option Args:
     *     error (function):
     *         A function to call if fetching a page fails. This must take
     *         ``collection, xhr`` arguments.
     *
     *     success (function):
     *         A function to call if fetching a page succeeds.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async fetchNext(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.RepositoryCommits.fetchNext was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.fetchNext(newOptions));
        }

        if (this.canFetchNext()) {
            this.options.start = this._nextStart;

            await this.fetch({
                remove: false,
            });

            this.busy = false;
        }
    }
});
