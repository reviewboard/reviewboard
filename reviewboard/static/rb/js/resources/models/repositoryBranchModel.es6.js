/**
 * A branch in a repository.
 *
 * Model Attributes:
 *     name (string):
 *         The name of the branch.
 *
 *     commit (string):
 *         The ID of the commit on the tip of the branch.
 *
 *     isDefault (boolean):
 *         Whether this is the "default" branch for the repository (master,
 *         trunk, etc.).
 */
RB.RepositoryBranch = RB.BaseResource.extend({
    defaults() {
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

    /**
     * Parse the result from the server.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parse(rsp) {
        return {
            id: rsp.id,
            name: rsp.name,
            commit: rsp.commit,
            isDefault: rsp['default']
        };
    }
});
