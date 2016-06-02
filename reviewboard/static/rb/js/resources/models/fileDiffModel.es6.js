/**
 * Represents a FileDiff resource.
 *
 * These are read-only resources, and contain information on a per-file diff.
 *
 * Model Attributes:
 *     destFilename (string):
 *         The destination filename in the diff. This may be the same as
 *         sourceFilename.
 *
 *     sourceFilename (string):
 *         The original filename in the diff.
 *
 *     sourceRevision (string):
 *         The revision of the file this diff applies to.
 */
RB.FileDiff = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            destFilename: null,
            sourceFilename: null,
            sourceRevision: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'filediff',

    /**
     * Deserialize data from an API payload.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData: function(rsp) {
        return {
            destFilename: rsp.dest_file,
            sourceFilename: rsp.source_file,
            sourceRevision: rsp.source_revision
        };
    }
});
