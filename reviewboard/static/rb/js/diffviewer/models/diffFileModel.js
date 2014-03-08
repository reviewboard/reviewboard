/*
 * A model for a single file in a diff.
 */
RB.DiffFile = Backbone.Model.extend({
    defaults: {
        binary: false,
        commentCounts: null,
        deleted: false,
        depotFilename: null,
        destFilename: null,
        destRevision: null,
        filediff: null,
        index: null,
        interfilediff: null,
        newfile: false,
        forceInterdiff: null,
        forceInterdiffRevision: null
    },

    /*
     * Parse the data given to us by the server.
     */
    parse: function(rsp) {
        return {
            binary: rsp.binary,
            commentCounts: rsp.comment_counts,
            deleted: rsp.deleted,
            depotFilename: rsp.depot_filename,
            destFilename: rsp.dest_filename,
            destRevision: rsp.dest_revision,
            filediff: rsp.filediff,
            id: rsp.id,
            index: rsp.index,
            interfilediff: rsp.interfilediff,
            newfile: rsp.newfile,
            revision: rsp.revision,
            forceInterdiff: rsp.force_interdiff,
            forceInterdiffRevision: rsp.interdiff_revision
        };
    }
});
