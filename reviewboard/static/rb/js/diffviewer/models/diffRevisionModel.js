/*
 * A model representing the viewed revision of a diff.
 */
RB.DiffRevision = Backbone.Model.extend({
    defaults: {
        revision: null,
        interdiffRevision: null,
        latestRevision: null,
        isInterdiff: false,
        isDraftDiff: false
    },

    /*
     * Parse the data given to us by the server.
     */
    parse: function(rsp) {
        return {
            revision: rsp.revision,
            interdiffRevision: rsp.interdiff_revision,
            latestRevision: rsp.latest_revision,
            isInterdiff: rsp.is_interdiff,
            isDraftDiff: rsp.is_draft_diff
        };
    }
});
