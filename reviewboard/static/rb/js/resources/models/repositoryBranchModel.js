/*
 * A branch in a repository.
 */
RB.RepositoryBranch = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            name: null,
            commit: null,
            isDefault: false
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'branches',

    deserializedAttrs: [
        'id',
        'name',
        'commit',
        'isDefault'
    ],

    serializedAttrs: [
        'id',
        'name',
        'commit',
        'isDefault'
    ],

    attrToJsonMap: {
        'isDefault': 'default'
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
