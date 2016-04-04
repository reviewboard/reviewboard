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
     * Fetch the next page of results.
     *
     * This can be called multiple times. If this is called when a fetch is
     * already in progress, it's a no-op. Otherwise, if there are more commits
     * to load, it will fetch them and add them to the bottom of the
     * collection.
     */
    fetchNext() {
        if (!this.busy && !this.complete && this.models.length) {
            let nextStart = this.models[this.models.length - 1].get('parent');

            if (nextStart === '') {
                this.complete = true;
            } else {
                this.options.start = nextStart;

                this.fetch({
                    remove: false,
                    success: () => this.busy = false
                });
            }
        }
    }
});
