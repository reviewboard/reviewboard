(function() {


/**
 * A history entry in a diff between two sets of commits.
 *
 * Attributes:
 *     entryType (string):
 *         The type of entry.
 *
 *     newCommitID (string):
 *         The commit ID of the new commit in the entry (if any).
 *
 *     oldCommitID (string):
 *         The commit ID of the old commit in the entry (if any).
 */
RB.CommitHistoryDiffEntry = Backbone.Model.extend({
    defaults: {
        entryType: null,
        newCommitID: null,
        oldCommitID: null,
    },

    /**
     * Parse the response.
     *
     * Args:
     *     rsp (object):
     *         The raw response from the server.
     *
     * Returns:
     *     object:
     *     The parsed attributes.
     */
    parse(rsp) {
        return {
            entryType: rsp.entry_type,
            newCommitID: rsp.new_commit_id,
            oldCommitID: rsp.old_commit_id,
        };
    },

    /**
     * Return the symbol representing this entry.
     *
     * Returns:
     *     string:
     *     The symbol representing this entry.
     */
    getSymbol() {
        const entryType = this.get('entryType');
        return RB.CommitHistoryDiffEntry.HISTORY_SYMBOL_MAP[entryType] || null;
    },
}, {
    ADDED: 'added',
    REMOVED: 'removed',
    MODIFIED: 'modified',
    UNMODIFIED: 'unmodified',
});


const symbolMap = {};

symbolMap[RB.CommitHistoryDiffEntry.ADDED] = '+';
symbolMap[RB.CommitHistoryDiffEntry.REMOVED] = '-';
symbolMap[RB.CommitHistoryDiffEntry.MODIFIED] = '~';
symbolMap[RB.CommitHistoryDiffEntry.UNMODIFIED] = ' ';

RB.CommitHistoryDiffEntry.HISTORY_SYMBOL_MAP = symbolMap;


})();
