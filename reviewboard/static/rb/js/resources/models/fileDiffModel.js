/*
 * Represents a FileDiff resource.
 *
 * These are read-only resources, and contain information on a per-file diff.
 */
RB.FileDiff = RB.BaseResource.extend({
    defaults: function () {
        return _.defaults({
            /*
             * The destination filename in the diff.
             *
             * This may be the same as sourceFilename.
             */
            destFilename: null,

            /* The original filename in the diff. */
            sourceFilename: null,

            /* The revision of the file this diff applies to. */
            sourceRevision: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'filediff',

    /*
     * Deserializes data from an API payload.
     */
    parseResourceData: function(rsp) {
        return {
            destFilename: rsp.dest_file,
            sourceFilename: rsp.source_file,
            sourceRevision: rsp.source_revision
        };
    }
});
