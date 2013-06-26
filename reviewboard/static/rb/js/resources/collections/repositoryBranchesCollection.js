/*
 * A collection of branches in a repository.
 */
RB.RepositoryBranches = Backbone.Collection.extend({
    model: RB.RepositoryBranch,

    parse: function(response) {
        return response.branches;
    }
});
