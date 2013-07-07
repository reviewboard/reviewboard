/*
 * A branch in a repository.
 */
RB.RepositoryBranch = Backbone.Model.extend({
    defaults: {
        name: null,
        commit: null,
        'default': false
    }
});
