/*
 * A branch in a repository.
 */
RB.RepositoryBranch = Backbone.Model.extend({
    defaults: {
        name: null,
        commit: null,
        isDefault: false
    },

    /*
     * Parse the result from the server.
     */
    parse: function(response) {
        return {
            id: response.id,
            name: response.name,
            commit: response.commit,
            isDefault: response['default']
        };
    }
});
