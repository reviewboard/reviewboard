/*
 * A model for a single commit in a diff.
 */
RB.DiffCommit = Backbone.Model.extend({
    defaults: function() {
        return {
            // The name of the commit's author.
            authorName: null,
            // The revision/SHA of the commit.
            commitId: null,
            // The commit message.
            description: null,
            // The total line counts.
            lineCounts: {
                // The number of delete lines.
                deleted: 0,
                // The number of equal lines.
                equal: 0,
                // The number of inserted lines.
                inserted: 0,
                // The number of replaced lines.
                replaced: 0
            },
            // A one-line summary of the commit message.
            summary: null
        };
    },

    /*
     * Get the total line count.
     */
    getTotalLineCount: function() {
        var sum = 0,
            property;

        for (property in this.attributes.lineCounts) {
            if (this.attributes.lineCounts.hasOwnProperty(property)) {
                sum += this.attributes.lineCounts[property];
            }
        }

        return sum;
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
            lineCounts: {
                deleted: rsp.delete_count,
                equal: rsp.equal_count,
                inserted: rsp.insert_count,
                replaced: rsp.replace_count
            },
            summary: summary
        };
    }
});
