/*
 * A collection of branches in a repository.
 */
RB.RepositoryBranches = RB.BaseCollection.extend({
    model: RB.RepositoryBranch,

    parse: function(response) {
        return response.branches;
    }
});
