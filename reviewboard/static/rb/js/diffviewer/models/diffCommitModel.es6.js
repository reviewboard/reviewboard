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
 *     commitMessageBody (string):
 *         The commit message body, without the summary.
 *
 *         Version Added:
 *             6.0
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
        commitMessageBody: null,
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
        const commitMessage = attrs.commit_message.trim();
        const i = commitMessage.indexOf('\n');

        let summary = (
            i === -1
            ? commitMessage
            : commitMessage.substr(0, i)
        ).trim();

        if (summary.length > MAX_SUMMARY_LEN) {
            summary = summary.substr(0, MAX_SUMMARY_LEN - 3) + '...';
        }

        const body = (
            i === -1
            ? null
            : commitMessage.substr(i).trim());

        return {
            authorName: attrs.author_name,
            commitID: attrs.commit_id,
            commitMessage: commitMessage,
            commitMessageBody: body,
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
