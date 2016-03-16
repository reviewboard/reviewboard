/**
 * A collection of branches in a repository.
 */
RB.RepositoryBranches = RB.BaseCollection.extend({
    model: RB.RepositoryBranch,

    /**
     * Parse the response from the server.
     *
     * Args:
     *     response (object):
     *         Response, parsed from the JSON returned by the server.
     *
     * Returns:
     *     Array of object:
     *     An array of objects parsed that will be parsed to create each model.
     */
    parse(response) {
        return response.branches;
    }
});
