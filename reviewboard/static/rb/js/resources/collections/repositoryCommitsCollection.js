/*
 * A collection of commits in a repository.
 *
 * This is expected to be used in an ephemeral manner to get a list of commits
 * from a given start point (usually corresponding to some branch in the
 * repository).
 *
 * TODO: add additional stuff in here to fetch the next page of commits
 * on-demand.
 */
RB.RepositoryCommits = Backbone.Collection.extend({
    model: RB.RepositoryCommit,

    initialize: function(models, options) {
        Backbone.Collection.prototype.initialize.call(this, models, options);
        this.options = options;
    },

    parse: function(response) {
        return response.commits;
    },

    url: function() {
        return this.options.urlBase + '?start=' + this.options.start;
    }
});
