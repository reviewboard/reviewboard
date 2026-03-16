/**
 * Represents a FileDiff resource.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import {
    type BaseResourceAttrs,
    type BaseResourceResourceData,
    BaseResource,
} from './baseResourceModel';


/**
 * Attributes for the FileDiff model.
 *
 * Version Added:
 *     8.0
 */
export interface FileDiffAttrs extends BaseResourceAttrs {
    /**
     * The destination filename in the diff.
     *
     * This may be the same as ``sourceFilename``.
     */
    destFilename: string;

    /** The original filename in the diff. */
    sourceFilename: string;

    /** The revision of the file this diff applies to. */
    sourceRevision: string;
}


/**
 * Resource data for the FileDiff model.
 *
 * Version Added:
 *     8.0
 */
export interface FileDiffResourceData extends BaseResourceResourceData {
    dest_file: string;
    source_file: string;
    source_revision: string;
}


/**
 * Represents a FileDiff resource.
 *
 * These are read-only resources, and contain information on a per-file diff.
 */
@spina
export class FileDiff extends BaseResource<
    FileDiffAttrs,
    FileDiffResourceData
> {
    static defaults: Result<Partial<FileDiffAttrs>> = {
        destFilename: null,
        sourceFilename: null,
        sourceRevision: null,
    };

    static rspNamespace = 'filediff';

    static attrToJsonMap: Record<string, string> = {
        destFilename: 'dest_file',
        sourceFilename: 'source_file',
        sourceRevision: 'source_revision',
    };

    static deserializedAttrs = [
        'destFilename',
        'sourceFilename',
        'sourceRevision',
    ];
}
