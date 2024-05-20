/**
 * A branch in a repository.
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
 * Attributes for the RepositoryBranch model.
 *
 * Version Added:
 *     8.0
 */
export interface RepositoryBranchAttrs extends BaseResourceAttrs {
    /** The ID of the commit on the tip of the branch. */
    commit: string;

    /**
     * Whether this is the "default" branch for the repository.
     *
     * Most VCS systems have a concept of a default branch (master, main,
     * trunk, etc.). This is used to show the default branch for the initial
     * load.
     */
    isDefault: boolean;

    /** The name of the branch. */
    name: string;
}


/**
 * Resource data for the RepositoryBranch model.
 *
 * Version Added:
 *     8.0
 */
export interface RepositoryBranchResourceData
extends BaseResourceResourceData {
    commit: string;
    default: boolean;
    name: string;
}


/**
 * A branch in a repository.
 */
@spina
export class RepositoryBranch extends BaseResource<
    RepositoryBranchAttrs,
    RepositoryBranchResourceData,
> {
    static defaults: Result<Partial<RepositoryBranchAttrs>> = {
        commit: null,
        isDefault: false,
        name: null,
    };

    static rspNamespace = 'branches';

    static deserializedAttrs = [
        'commit',
        'isDefault',
        'name',
    ];

    static serializedAttrs = [
        'commit',
        'isDefault',
        'name',
    ];

    static attrToJsonMap: Record<string, string> = {
        'isDefault': 'default',
    };
}
