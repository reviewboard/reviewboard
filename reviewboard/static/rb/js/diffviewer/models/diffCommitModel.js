/*
 * A model for a single commit in a diff.
 */
RB.DiffCommit = Backbone.Model.extend({
    defaults: {
        // The name of the commit's author.
        authorName: null,
        // The revision/SHA of the commit.
        commitId: null,
        // The commit message.
        description: null,
        // A one-line summary of the commit message.
        summary: null
    },

    /*
     * Parse the data given to use by the server.
     */
    parse: function(rsp) {
        var summary = rsp.description.split('\n', 1)[0].trim();

        if (summary.length > 80) {
            summary = summary.substr(0, 77) + '...';
        }

        return {
            authorName: rsp.author_name,
            commitId: rsp.commit_id,
            description: rsp.description,
            summary: summary
        };
    }
});
