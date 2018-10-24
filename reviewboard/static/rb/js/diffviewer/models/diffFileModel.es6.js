/**
 * A model for a single file in a diff.
 *
 * Model Attributes:
 *     baseFileDiffID (number):
 *         An optional primary key of a :py:class:`~reviewboard.diffviewer.
 *         models.filediff.FileDiff` for generating a diff spanning multiple
 *         commits.
 *
 *     binary (boolean):
 *         Whether or not this is a binary file.
 *
 *     commentCounts (Array of number):
 *         The counts of each comment type.
 *
 *     deleted (boolean):
 *         Whether or not the file was deleted.
 *
 *     depotFilename (string):
 *         The file's path in the repository.
 *
 *     destFilename (string):
 *         The destination file path. This will differ from ``depotFilename``
 *         in the case of a move or rename.
 *
 *     filediff (object):
 *         A serailized :py:class:`~reviewboard.diffviewer.models.filediff.
 *         FileDiff` representing this file.
 *
 *     index (number):
 *         The file's index in the diff.
 *
 *     interfilediff (object):
 *         An optional serialized :py:class:`~reviewboard.diffviewer.models.
 *         filediff.FileDiff` for interidffing.
 *
 *     newfile (boolean):
 *         Whether or not the file is newly created.
 *
 *     revision (number):
 *         The base revision of the file.
 */
RB.DiffFile = Backbone.Model.extend({
    defaults: {
        baseFileDiffID: null,
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
        forceInterdiffRevision: null,
    },

    /**
     * Parse the response into model attributes.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     The model attributes.
     */
    parse(rsp) {
        return {
            binary: rsp.binary,
            baseFileDiffID: rsp.base_filediff_id,
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
            forceInterdiffRevision: rsp.interdiff_revision,
        };
    },
});
