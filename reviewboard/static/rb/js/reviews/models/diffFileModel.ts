/**
 * A model for a single file in a diff.
 */

import { BaseModel, ModelAttributes, spina } from '@beanbag/spina';


/**
 * Serialized information about a FileDiff.
 *
 * Version Added:
 *     7.0
 */
interface SerializedFileDiff {
    /** The primary key of the FileDiff model in the database. */
    id: number;

    /**
     * The numeric revision of the diff.
     *
     * This represents the diff revisions on the review request, starting at 1.
     */
    revision: number;
}


/**
 * Attributes for the DiffFile model.
 *
 * Version Added:
 *     7.0
 */
export interface DiffFileAttrs extends ModelAttributes {
    /**
     * The ID of the FileDiff for comparing commits.
     *
     * This is an optional primary key of a
     * :py:class:`~reviewboard.diffviewer.models.filediff.FileDiff`, used when
     * generating a diff across a subset of commits.
     */
    baseFileDiffID: number | null;

    /** Whether or not this is a binary file. */
    binary: boolean;

    /**
     * The serialized comments.
     *
     * This will be changing in a future commit.
     */
    commentCounts: object[] | null;

    /** Whether or not the file was deleted. */
    deleted: boolean;

    /** The filename for the original version of the file. */
    depotFilename: string | null;

    /** The filename for the modified version of the file. */
    destFilename: string | null;

    /** The revision for the modified version of the file. */
    destRevision: string | null;

    /** Information about the filediff. */
    filediff: SerializedFileDiff | null;

    /**
     * Whether to force an interdiff for this file.
     *
     * This is used in order to force the interdiff to render when files are
     * reverted in subsequent changes.
     */
    forceInterdiff: boolean | null;

    /** The revision to force the interdiff to. */
    forceInterdiffRevision: number | null;

    /** The index of the file in the diff. */
    index: number | null;

    /** Information about the interdiff, if present. */
    interfilediff: SerializedFileDiff | null;

    /** Whether this file is newly added. */
    newfile: boolean;

    /** Whether the diff has been published or not. */
    public: boolean;

    /** The revision for the original version of the file. */
    revision: string | null;
}


/**
 * Serialized resource data as returned from the server.
 *
 * Version Added:
 *     7.0
 */
export interface DiffFileResourceData {
    base_filediff_id: number;
    binary: boolean;
    comment_counts: object[];
    deleted: boolean;
    depot_filename: string;
    dest_filename: string;
    dest_revision: string;
    filediff: SerializedFileDiff;
    force_interdiff: boolean;
    id: number;
    index: number;
    interdiff_revision: number;
    interfilediff: SerializedFileDiff;
    newfile: boolean;
    public: boolean;
    revision: string;
}


/**
 * A model for a single file in a diff.
 */
@spina
export class DiffFile extends BaseModel<DiffFileAttrs> {
    static defaults: DiffFileAttrs = {
        baseFileDiffID: null,
        binary: false,
        commentCounts: null,
        deleted: false,
        depotFilename: null,
        destFilename: null,
        destRevision: null,
        filediff: null,
        forceInterdiff: null,
        forceInterdiffRevision: null,
        index: null,
        interfilediff: null,
        newfile: false,
        public: false,
        revision: null,
    };

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
    parse(
        rsp: DiffFileResourceData,
    ): DiffFileAttrs {
        return {
            baseFileDiffID: rsp.base_filediff_id,
            binary: rsp.binary,
            commentCounts: rsp.comment_counts,
            deleted: rsp.deleted,
            depotFilename: rsp.depot_filename,
            destFilename: rsp.dest_filename,
            destRevision: rsp.dest_revision,
            filediff: rsp.filediff,
            forceInterdiff: rsp.force_interdiff,
            forceInterdiffRevision: rsp.interdiff_revision,
            id: rsp.id,
            index: rsp.index,
            interfilediff: rsp.interfilediff,
            newfile: rsp.newfile,
            public: rsp.public,
            revision: rsp.revision,
        };
    }
}
