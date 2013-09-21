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
        newfile: false
    },

    /*
     * Parse the data given to us by the server.
     */
    parse: function(rsp) {
        return {
            newfile: rsp.newfile,
            binary: rsp.binary,
            deleted: rsp.deleted,
            id: rsp.id,
            depotFilename: rsp.depot_filename,
            destFilename: rsp.dest_filename,
            destRevision: rsp.dest_revision,
            revision: rsp.revision,
            filediff: rsp.filediff,
            interfilediff: rsp.interfilediff,
            index: rsp.index,
            commentCounts: rsp.comment_counts
        };
    }
});
