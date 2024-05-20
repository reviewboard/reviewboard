/**
 * A diff to be uploaded to a server.
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
 * Attributes for the Diff model.
 *
 * Version Added:
 *     8.0
 */
export interface DiffAttrs extends BaseResourceAttrs {
    /** The base directory for diff filenames within the repository. */
    basedir: string;

    /** The diff file itself (used when creating a new diff). */
    diff: File | null;

    /** The parent diff file (used when creating a new diff). */
    parentDiff: File | null;
}


/**
 * Resource data for the Diff model.
 *
 * Version Added:
 *     8.0
 */
export interface DiffResourceData extends BaseResourceResourceData {
    basedir: string;
}


/**
 * A diff to be uploaded to a server.
 *
 * For now, this is used only for uploading new diffs.
 *
 * It is expected that parentObject will be set to a ReviewRequest instance.
 */
@spina
export class Diff extends BaseResource<
    DiffAttrs,
    DiffResourceData
> {
    static defaults: Result<Partial<DiffAttrs>> = {
        basedir: null,
        diff: null,
        parentDiff: null,
    };

    static rspNamespace = 'diff';

    static attrToJsonMap: Record<string, string> = {
        diff: 'path',
        parentDiff: 'parent_diff_path',
    };

    static serializedAttrs = ['basedir', 'diff', 'parentDiff'];

    static payloadFileKeys = ['path', 'parent_diff_path'];

    static listKey: Result<string> = 'diffs';

    /**
     * Return a user-facing error string for a given server response.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     string:
     *     A string to show to the user.
     */
    getErrorString(
        rsp: {
            err: {
                code: number;
                msg: string;
            };
            file: string;
            revision: string;
        },
    ): string {
        if (rsp.err.code === RB.APIErrors.REPO_FILE_NOT_FOUND) {
            return _`
                The file "${rsp.file}" (revision ${rsp.revision}) was not
                found in the repository.
            `;
        }

        return rsp.err.msg;
    }
}
