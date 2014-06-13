/*
 * A collection of commits in a repository.
 *
 * This is expected to be used in an ephemeral manner to get a list of commits
 * from a given start point (usually corresponding to some branch in the
 * repository).
 */
RB.RepositoryCommits = RB.BaseCollection.extend({
    model: RB.RepositoryCommit,

    /*
     * Initialize the collection.
     */
    initialize: function(models, options) {
        Backbone.Collection.prototype.initialize.call(this, models, options);
        this.options = options;
        this.busy = false;
        this.complete = false;
    },

    /*
     * Parse the response.
     */
    parse: function(response) {
        return response.commits;
    },

    /*
     * Get the URL to fetch for the next page of results.
     */
    url: function() {
        var args = [];

        if (this.options.start !== undefined) {
            args.push('start=' + encodeURIComponent(this.options.start));
        }

        if (this.options.branch !== undefined) {
            args.push('branch=' + encodeURIComponent(this.options.branch));
        }

        return this.options.urlBase + '?' + args.join('&');
    },

    /*
     * Fetch the next page of results.
     *
     * This can be called multiple times. If this is called when a fetch is
     * already in progress, it's a no-op. Otherwise, if there are more commits
     * to load, it will fetch them and add them to the bottom of the
     * collection.
     */
    fetchNext: function() {
        var nextStart;

        if (!this.busy && !this.complete && this.models.length) {
            nextStart = this.models[this.models.length - 1].get('parent');

            if (nextStart === '') {
                this.complete = true;
            } else {
                this.options.start = nextStart;

                this.fetch({
                    remove: false,
                    success: function() {
                        this.busy = false;
                    }
                }, this);
            }
        }
    }
});
