/**
 * A model for a single file in a diff.
 */

import {
    type ModelAttributes,
    type Result,
    BaseModel,
    spina,
} from '@beanbag/spina';

import { type SerializedDiffComment } from './commentData';


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


/** The set of serialized comment blocks in the diff. */
type SerializedDiffCommentBlocks = { [key: string]: SerializedDiffComment };


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

    /** Whether or not the file was deleted. */
    deleted: boolean;

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

    /**
     * The filename for the modified version of the file.
     *
     * Version Changed:
     *     7.0:
     *     This attribute was renamed (was ``destFilename``).
     */
    modifiedFilename: string | null;

    /**
     * The revision for the modified version of the file.
     *
     * Version Changed:
     *     7.0:
     *     This attribute was renamed (was ``destRevision``).
     */
    modifiedRevision: string | null;

    /** Whether this file is newly added. */
    newfile: boolean;

    /**
     * The filename for the original version of the file.
     *
     * Version Changed:
     *     7.0:
     *     This attribute was renamed (was ``depotFilename``).
     */
    origFilename: string | null;

    /**
     * The revision for the original version of the file.
     *
     * Version Changed:
     *     7.0:
     *     This attribute was renamed (was ``revision``).
     */
    origRevision: string | null;

    /** Whether the diff has been published or not. */
    public: boolean;

    /** The set of serialized comment blocks in the diff. */
    serializedCommentBlocks: SerializedDiffCommentBlocks | null;
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
    deleted: boolean;
    filediff: SerializedFileDiff;
    force_interdiff: boolean;
    id: number;
    index: number;
    interdiff_revision: number;
    interfilediff: SerializedFileDiff;
    modified_filename: string;
    modified_revision: string;
    newfile: boolean;
    orig_filename: string;
    orig_revision: string;
    public: boolean;
    serialized_comment_blocks: SerializedDiffCommentBlocks | null;
}


/**
 * A model for a single file in a diff.
 */
@spina
export class DiffFile extends BaseModel<DiffFileAttrs> {
    static defaults: Result<Partial<DiffFileAttrs>> = {
        baseFileDiffID: null,
        binary: false,
        deleted: false,
        filediff: null,
        forceInterdiff: null,
        forceInterdiffRevision: null,
        index: null,
        interfilediff: null,
        modifiedFilename: null,
        modifiedRevision: null,
        newfile: false,
        origFilename: null,
        origRevision: null,
        public: false,
        serializedCommentBlocks: null,
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
            deleted: rsp.deleted,
            filediff: rsp.filediff,
            forceInterdiff: rsp.force_interdiff,
            forceInterdiffRevision: rsp.interdiff_revision,
            id: rsp.id,
            index: rsp.index,
            interfilediff: rsp.interfilediff,
            modifiedFilename: rsp.modified_filename,
            modifiedRevision: rsp.modified_revision,
            newfile: rsp.newfile,
            origFilename: rsp.orig_filename,
            origRevision: rsp.orig_revision,
            public: rsp.public,
            serializedCommentBlocks: rsp.serialized_comment_blocks,
        };
    }
}
