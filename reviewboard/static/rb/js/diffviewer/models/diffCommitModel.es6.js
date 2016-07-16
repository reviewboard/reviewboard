/**
 * A model for a single commit in a diff.
 *
 * Attributes:
 *     authorName (string):
 *         The name of the commit's author.
 *
 *     commitID (string):
 *         A unique identifier for the commit. This is usually a SHA-1 hash.
 *
 *     description (string):
 *         The full commit message.
 *
 *     historyEntrySymbol (string):
 *         The symbol for the ``historyEntryType`` attribute.
 *
 *     historyEntryType (string):
 *         The type of the history entry for the commit. This is one of:
 *
 *         * ``'added'``
 *         * ``'deleted'``
 *         * ``'unmodified'``
 *
 *         This attribute is used for showing the interdiff between two commit
 *         histories.
 *
 *         When there is no interdiff, this will always be ``'unmodified'``.
 *
 *     lineCounts (object):
 *         The total line counts of the commit. This object contains the
 *         following keys:
 *             ``deleted`` (number):
 *                 The number of deleted lines.
 *
 *             ``equal`` (number):
 *                 The number of equal (unmodified) lines.
 *
 *             ``inserted`` (number):
 *                 The number of inserted lines.
 *
 *             ``replaced`` (number):
 *                 The number of replaced lines.
 *
 *     summary (string):
 *         A one-line summary of the commit message, limited to 80 characters.
 */
RB.DiffCommit = Backbone.Model.extend({
    defaults() {
        return {
            authorName: null,
            commitID: null,
            description: null,
            historyEntrySymbol: null,
            historyEntryType: null,
            lineCounts: {
                deleted: 0,
                equal: 0,
                inserted: 0,
                replaced: 0
            },
            summary: null
        };
    },

    /**
     * Return the total line count.
     *
     * Returns:
     *     number: The sum of all line count types in the commit.
     */
    getTotalLineCount() {
        return Object.values(this.get('lineCounts'))
            .reduce((a, b) => a + b, 0);
    },

    /**
     * Parse the data given to use by the server.
     *
     * Returns:
     *     object:
     *     The parsed attributes.
     */
    parse(rsp) {
        let summary = rsp.description.split('\n', 1)[0].trim();

        if (summary.length > 80) {
            summary = summary.substr(0, 77) + '...';
        }

        let historyEntrySymbol;

        switch (rsp.type) {
            case 'added':
                historyEntrySymbol = '+';
                break;

            case 'removed':
                historyEntrySymbol = '-';
                break;

            default:
                historyEntrySymbol = ' ';
                break;
        }

        return {
            authorName: rsp.author_name,
            commitID: rsp.commit_id,
            description: rsp.description,
            historyEntrySymbol: historyEntrySymbol,
            historyEntryType: rsp.type,
            lineCounts: {
                deleted: rsp.delete_count,
                equal: rsp.equal_count,
                inserted: rsp.insert_count,
                replaced: rsp.replace_count
            },
            summary: summary
        };
    },

    /**
     * Determine if the description contains more text than the summary.
     *
     * Returns:
     *     bool: Whether or not the description and summary differ.
     */
    isSummarized() {
        return this.get('summary').trim() !== this.get('description').trim();
    }
});
