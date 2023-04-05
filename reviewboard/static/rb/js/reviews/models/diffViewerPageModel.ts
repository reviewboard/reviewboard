/**
 * The model for the diff viewer page.
 */
import { spina } from '@beanbag/spina';

import {
    ReviewablePage,
    ReviewablePageAttrs,
    ReviewablePageParseData,
} from './reviewablePageModel';


/** Attributes for the DiffViewerPage model. */
export interface DiffViewerPageAttrs extends ReviewablePageAttrs {
    /**
     * Whether to collapse all chunks to only modified ones.
     *
     * If this is ``false``, all lines in the file will be shown.
     */
    allChunksCollapsed?: boolean;

    /** Whether the diff can be downloaded given the current revision state. */
    canDownloadDiff?: boolean;

    /**
     * Whether the user can toggle the display of extra whitespace.
     *
     * If ``true``, the user can toggle on or off the display of mismatched
     * indentation and trailing whitespace.
     */
    canToggleExtraWhitespace?: boolean;

    /** A list of filename patterns to filter the diff viewer. */
    filenamePatterns?: string[];

    /** The total number of diffs. */
    numDiffs?: number;
}


/** The format of data passed in to the object. */
interface DiffViewerPageParseData extends ReviewablePageParseData {
    // TODO: update these as sub-objects are converted to TS.
    allChunksCollapsed: boolean;
    canToggleExtraWhitespace: boolean;
    comments_hint: object;
    commit_history_diff: object[];
    commits: object[];
    filename_patterns: string[];
    files: object[];
    num_diffs: number;
    pagination: object;
    revision: {
        revision: number,
        interdiff_revision: number,
        is_interdiff: number,
    };
}


/** The options for loading a new diff revision. */
interface LoadDiffRevisionOptions {
    /** The primary key of the base commit to base the diff off of. */
    baseCommitID?: number;

    /** A comma-separated list of filenames or patterns to load. */
    filenamePatterns?: string;

    /**
     * The page number to load.
     *
     * Defaults to the first page.
     */
    page?: number;

    /**
     * The base revision.
     *
     * If displaying an interdiff, this will be the first revision in the
     * range.
     */
    revision?: number;

    /**
     * The optional interdiff revision.
     *
     * If displaying an interdiff, this will be the last revision in the
     * range.
     */
    interdiffRevision?: number;

    /** The primary key of the tip commit to base the diff off of. */
    tipCommitID?: number;
}


/**
 * The model for the diff viewer page.
 *
 * This handles all attribute storage and diff context parsing needed to
 * display and update the diff viewer.
 */
@spina
export class DiffViewerPage extends ReviewablePage<DiffViewerPageAttrs> {
    static defaults: DiffViewerPageAttrs = {
        allChunksCollapsed: false,
        canDownloadDiff: false,
        canToggleExtraWhitespace: false,
        filenamePatterns: null,
        numDiffs: 1,
    };

    /**********************
     * Instance variables *
     **********************/

    /** The hint for comments in other revisions. */
    commentsHint: RB.DiffCommentsHint;

    /** The diff of all the files between currently-shown commits. */
    commitHistoryDiff: RB.CommitHistoryDiffEntryCollection;

    /** The set of commits attached to the review request. */
    commits: RB.DiffFCommitCollection;

    /** The set of reviewables for currently-shown files. */
    diffReviewables: RB.DiffReviewableCollection;

    /** The set of currently-shown files. */
    files: RB.DiffFileCollection;

    /** Paginator for all of the diff files. */
    pagination: RB.Pagination;

    /** The current diff revision. */
    revision: RB.DiffRevision;

    /**
     * Handle pre-parse initialization.
     *
     * This defines child objects for managing state related to the page
     * prior to parsing the provided attributes payload and initializing
     * the instance.
     */
    preinitialize() {
        this.commentsHint = new RB.DiffCommentsHint();
        this.commits = new RB.DiffCommitCollection();
        this.commitHistoryDiff = new RB.CommitHistoryDiffEntryCollection();
        this.files = new RB.DiffFileCollection();
        this.pagination = new RB.Pagination();
        this.revision = new RB.DiffRevision();
    }

    /**
     * Initialize the page.
     *
     * This will begin listening for events on the page and set up default
     * state.
     */
    initialize(...args: [DiffViewerPageAttrs, object]) {
        super.initialize(...args);

        this.diffReviewables = new RB.DiffReviewableCollection([], {
            reviewRequest: this.get('reviewRequest'),
        });
        this.diffReviewables.watchFiles(this.files);
    }

    /**
     * Parse the data for the page.
     *
     * Args:
     *     rsp (DiffViewerPageParseData):
     *         The payload to parse.
     *
     * Returns:
     *     DiffViewerPageAttrs:
     *     The returned attributes.
     */
    parse(
        rsp: DiffViewerPageParseData,
    ): Partial<DiffViewerPageAttrs> {
        const attrs = _.extend(
            this._parseDiffContext(rsp),
            super.parse(rsp));

        if (rsp.allChunksCollapsed !== undefined) {
            attrs.allChunksCollapsed = rsp.allChunksCollapsed;
        }

        if (rsp.canToggleExtraWhitespace !== undefined) {
            attrs.canToggleExtraWhitespace = rsp.canToggleExtraWhitespace;
        }

        return attrs;
    }

    /**
     * Load a new diff from the server.
     *
     * Args:
     *     options (LoadDiffRevisionOptions):
     *         The options for the diff to load.
     */
    loadDiffRevision(options: LoadDiffRevisionOptions = {}) {
        const reviewRequestURL = this.get('reviewRequest').url();
        const queryData = [];

        if (options.revision) {
            queryData.push({
                name: 'revision',
                value: options.revision,
            });
        }

        if (options.interdiffRevision) {
            queryData.push({
                name: 'interdiff-revision',
                value: options.interdiffRevision,
            });
        } else {
            if (options.baseCommitID) {
                queryData.push({
                    name: 'base-commit-id',
                    value: options.baseCommitID,
                });
            }

            if (options.tipCommitID) {
                queryData.push({
                    name: 'tip-commit-id',
                    value: options.tipCommitID,
                });
            }
        }

        if (options.page && options.page !== 1) {
            queryData.push({
                name: 'page',
                value: options.page,
            });
        }

        if (options.filenamePatterns) {
            queryData.push({
                name: 'filenames',
                value: options.filenamePatterns,
            });
        }

        const url = Djblets.buildURL({
            baseURL: `${reviewRequestURL}diff-context/`,
            queryData: queryData,
        });

        $.ajax(url)
            .done(rsp => this.set(this._parseDiffContext(rsp.diff_context)));
    }

    /**
     * Parse context for a displayed diff.
     *
     * Args:
     *     rsp (object):
     *         The payload to parse.
     *
     * Returns:
     *     object:
     *     The returned attributes.
     */
    _parseDiffContext(
        rsp: DiffViewerPageParseData,
    ): Partial<DiffViewerPageAttrs> {
        if (rsp.comments_hint) {
            this.commentsHint.set(this.commentsHint.parse(rsp.comments_hint));
        }

        if (rsp.files) {
            this.files.reset(rsp.files, {parse: true});
        }

        if (rsp.pagination) {
            this.pagination.set(this.pagination.parse(rsp.pagination));
        }

        if (rsp.revision) {
            this.revision.set(this.revision.parse(rsp.revision));
        }

        this.commitHistoryDiff.reset(rsp.commit_history_diff || [],
                                     {parse: true});

        if (rsp.commits) {
            /*
             * The RB.DiffCommitListView listens for the reset event on the
             * commits collection to trigger a render, so it must be updated
             * **after** the commit history is updated.
             */
            this.commits.reset(rsp.commits, {parse: true});
        }

        return {
            canDownloadDiff: (rsp.revision &&
                              rsp.revision.interdiff_revision === null),
            filenamePatterns: rsp.filename_patterns || null,
            numDiffs: rsp.num_diffs || 0,
        };
    }
}
