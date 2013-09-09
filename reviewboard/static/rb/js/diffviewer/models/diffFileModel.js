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
    }
});
