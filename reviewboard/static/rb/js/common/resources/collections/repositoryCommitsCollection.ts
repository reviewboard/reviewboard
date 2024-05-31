/**
 * A collection of commits in a repository.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import { BaseCollection } from '../../collections/baseCollection';
import { API } from '../../utils/apiUtils';
import {
    type RepositoryCommitAttrs,
    RepositoryCommit,
} from '../models/repositoryCommitModel';


/**
 * Options for the RepositoryCommits collection.
 *
 * Version Added:
 *     8.0
 */
export interface RepositoryCommitsOptions {
    /** The branch to fetch commits from. */
    branch?: string;

    /** The starting commit (which will be the most recent commit listed). */
    start?: string;

    /** The base URL to use. */
    urlBase: string;
}


/**
 * A collection of commits in a repository.
 *
 * This is expected to be used in an ephemeral manner to get a list of commits
 * from a given start point (usually corresponding to some branch in the
 * repository).
 */
@spina
export class RepositoryCommits extends BaseCollection<
    RepositoryCommit,
    RepositoryCommitsOptions
> {
    static model = RepositoryCommit;

    /**********************
     * Instance variables *
     **********************/

    /** The saved options. */
    options: RepositoryCommitsOptions;

    /** Whether all data has been fetched. */
    complete = false;

    /** The start commit to use to fetch the next page. */
    #nextStart: string | null = null;

    /**
     * Initialize the collection.
     *
     * Args:
     *     models (Array of object):
     *         Initial models for the collection.
     *
     *     options (Object):
     *         Options for the collection.
     *
     * Option Args:
     *     start (string):
     *         The start commit for fetching commit logs.
     *
     *     branch (string):
     *         The branch name for fetching commit logs.
     *
     *     urlBase (string):
     *         The base URL for the API request.
     */
    initialize(
        models: RepositoryCommit[] | RepositoryCommitAttrs[],
        options: RepositoryCommitsOptions,
    ) {
        super.initialize(models, options);
        this.options = options;
    }

    /**
     * Parse the response.
     *
     * Args:
     *     response (object):
     *         Response, parsed from the JSON returned by the server.
     *
     * Returns:
     *     Array of object:
     *     An array of commits.
     */
    parse(
        response: {
            commits: RepositoryCommitAttrs[],
        },
    ): RepositoryCommitAttrs[] {
        const commits = response.commits;

        this.#nextStart = commits[commits.length - 1].parent;
        this.complete = !this.#nextStart;

        return response.commits;
    }

    /**
     * Get the URL to fetch for the next page of results.
     *
     * Returns:
     *     string:
     *     The URL to fetch.
     */
    url(): Result<string> {
        const params: Record<string, string> = {};

        if (this.options.start !== undefined) {
            params.start = this.options.start;
        }

        if (this.options.branch !== undefined) {
            params.branch = this.options.branch;
        }

        return this.options.urlBase + '?' + $.param(params);
    }

    /**
     * Return whether another page of commits can be fetched.
     *
     * A page can only be fetched if there's at least 1 commit already
     * fetched, the last commit in the repository has not been fetched, and
     * another fetch operation isn't in progress.
     *
     * Version Added:
     *     4.0.3
     *
     * Returns:
     *     boolean:
     *     ``true`` if another page can be fetched. ``false`` if one cannot.
     */
    canFetchNext(): boolean {
        return !this.complete && this.models.length > 0;
    }

    /**
     * Fetch the next page of results.
     *
     * This can be called multiple times. If this is called when a fetch is
     * already in progress, it's a no-op. Otherwise, if there are more commits
     * to load, it will fetch them and add them to the bottom of the
     * collection.
     *
     * It's up to the caller to check :js:func:`canFetchNext()` before calling
     * this if they want callbacks to fire.
     *
     * Version Changed:
     *     8.0:
     *     Removed callbacks and the context parameter.
     *
     * Version Changed:
     *     5.0:
     *     Added the promise return value.
     *
     * Version Changed:
     *     4.0.3:
     *     Added the ``options`` argument with ``error`` and ``success``
     *     callbacks.
     *
     * Args:
     *     options (object, optional):
     *         Options for fetching the next page of results.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async fetchNext(
        options: Backbone.PersistenceOptions = {},
    ): Promise<void> {
        console.assert(
            !(options.success || options.error || options.complete),
            dedent`
                RB.RepositoryCommits.fetchNext was called using callbacks.
                This has been removed in Review Board 8.0 in favor of promises.
            `);

        if (this.canFetchNext()) {
            this.options.start = this.#nextStart;

            await this.fetch({
                remove: false,
            });
        }
    }
}
