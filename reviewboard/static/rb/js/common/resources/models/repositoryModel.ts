/**
 * A client-side representation of a repository on the server.
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
import {
    RepositoryBranches,
} from '../collections/repositoryBranchesCollection';
import {
    type RepositoryCommitsOptions,
    RepositoryCommits,
} from '../collections/repositoryCommitsCollection';


/**
 * Attributes for the Repository model.
 *
 * Version Added:
 *     7.0.1
 */
export interface RepositoryAttrs extends BaseResourceAttrs {
    /** Whether this repository is the fake "file attachments only" entry. */
    filesOnly: boolean;

    /** The URL prefix for the local site, if any. */
    localSitePrefix: string;

    /** The name of the repository. */
    name: string;

    /**
     * Whether this repository requires base directories.
     *
     * This will be set if posting diffs against this repository requires
     * the specification of a "base directory" (the relative path between
     * the repository root and the filenames in the diff file).
     */
    requiresBasedir: boolean;

    /**
     * Whether this repository requires specifying change numbers.
     */
    requiresChangeNumber: boolean;

    /** The name of the SCM that this repository uses. */
    scmtoolName: string;

    /**
     * Whether this repository supports the post-commit UI.
     */
    supportsPostCommit: boolean;
}


/**
 * Resource data for the Repository model.
 *
 * Version Added:
 *     7.0.1
 */
export interface RepositoryResourceData extends BaseResourceResourceData {
    name: string;
    requires_basedir: boolean;
    requires_change_number: boolean;
    supports_post_commit: boolean;
    tool: string;
}


/**
 * A client-side representation of a repository on the server.
 */
@spina
export class Repository extends BaseResource<
    RepositoryAttrs,
    RepositoryResourceData
> {
    static defaults: Result<Partial<RepositoryAttrs>> = {
        filesOnly: false,
        localSitePrefix: null,
        name: null,
        requiresBasedir: false,
        requiresChangeNumber: false,
        scmtoolName: null,
        supportsPostCommit: false,
    };

    static rspNamespace = 'repository';

    static attrToJsonMap: Record<string, string> = {
        name: 'name',
        requiresBasedir: 'requires_basedir',
        requiresChangeNumber: 'requires_change_number',
        scmtoolName: 'tool',
        supportsPostCommit: 'supports_post_commit',
    };

    static deserializedAttrs = [
        'name',
        'requiresBasedir',
        'requiresChangeNumber',
        'scmtoolName',
        'supportsPostCommit',
    ];

    static listKey = 'repositories';

    /**********************
     * Instance variables *
     **********************/

    /** The repository branches collection. */
    branches: RepositoryBranches;

    /**
     * Initialize the model.
     */
    initialize(
        attributes?: Partial<RepositoryAttrs>,
        options?: Backbone.CombinedModelConstructorOptions<
            unknown, this>,
    ) {
        super.initialize(attributes, options);

        this.branches = new RepositoryBranches();
        this.branches.url = _.result(this, 'url') + 'branches/';
    }

    /**
     * Return a collection of commits from a given starting point.
     *
     * Args:
     *     options (RepositoryCommitsOptions):
     *         Options for the commits collection.
     *
     * Returns:
     *     RB.RepositoryCommits:
     *     The commits collection.
     */
    getCommits(
        options: RepositoryCommitsOptions,
    ): RepositoryCommits {
        return new RepositoryCommits([], Object.assign({
            urlBase: `${this.getURL()}commits/`,
        }, options));
    }

    /**
     * Return the URL for syncing the model.
     *
     * Returns:
     *     string:
     *     The URL to use when syncing the model.
     */
    url(): string {
        const url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                    'api/repositories/';

        return this.isNew() ? url : `${url}${this.id}/`;
    }
}
