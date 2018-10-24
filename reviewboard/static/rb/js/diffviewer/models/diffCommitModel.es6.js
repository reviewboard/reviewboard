(function() {


const MAX_SUMMARY_LEN = 80;


/**
 * A representation of a single commit in a diff.
 *
 * Model Attributes:
 *     authorName (string):
 *         The name of the author of the commit.
 *
 *     commitID (string):
 *         The unique identifier for the commit.
 *
 *     commitMessage (string):
 *         The commit message.
 *
 *     parentID (string):
 *         The unique identifier of the parent commit.
 *
 *     summary (string):
 *         A one-line summary of the commit message.
 */
RB.DiffCommit = Backbone.Model.extend({
    defaults: {
        authorName: null,
        commitID: null,
        commitMessage: null,
        parentID: null,
        summary: null,
    },

    /**
     * Parse a commit.
     *
     * Args:
     *     attrs (object):
     *         The raw attributes to parse.
     *
     * Returns:
     *     object:
     *     The parsed attribute-value pairs.
     */
    parse(attrs) {
        let summary = attrs.commit_message.split('\n', 1)[0].trim();

        if (summary.length > MAX_SUMMARY_LEN) {
            summary = summary.substr(0, MAX_SUMMARY_LEN - 3) + '...';
        }

        return {
            authorName: attrs.author_name,
            commitID: attrs.commit_id,
            commitMessage: attrs.commit_message.trim(),
            id: attrs.id,
            parentID: attrs.parent_id,
            summary: summary,
        };
    },

    /**
     * Whether or not the commit message differs from the summary.
     *
     * Returns:
     *     boolean:
     *     Whether or not the commit message differs from the summary.
     */
    hasSummary() {
        return (this.get('summary') !== this.get('commitMessage'));
    },
});


})();
