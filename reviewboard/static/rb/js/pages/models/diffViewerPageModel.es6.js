/**
 * The model for the diff viewer page.
 *
 * This handles all attribute storage and diff context parsing needed to
 * display and update the diff viewer.
 *
 * Model Attributes:
 *     canDownloadDiff (boolean):
 *         Whether a diff file can be downloaded, given the current revision
 *         state.
 *
 *     numDiffs (number):
 *         The total number of diffs.
 */
RB.DiffViewerPage = RB.ReviewablePage.extend({
    defaults: _.defaults({
        canDownloadDiff: false,
        numDiffs: 1,
    }, RB.ReviewablePage.prototype.defaults),

    /**
     * Construct the page's instance.
     *
     * This defines child objects for managing state related to the page
     * prior to parsing the provided attributes payload and initializing
     * the instance.
     */
    constructor() {
        this.commentsHint = new RB.DiffCommentsHint();
        this.files = new RB.DiffFileCollection();
        this.pagination = new RB.Pagination();
        this.revision = new RB.DiffRevision();

        RB.ReviewablePage.apply(this, arguments);
    },

    /**
     * Initialize the page.
     *
     * This will begin listening for events on the page and set up default
     * state.
     */
    initialize() {
        RB.ReviewablePage.prototype.initialize.apply(this, arguments);

        this.diffReviewables = new RB.DiffReviewableCollection([], {
            reviewRequest: this.get('reviewRequest'),
        });
        this.diffReviewables.watchFiles(this.files);
    },

    /**
     * Parse the data for the page.
     *
     * Args:
     *     rsp (object):
     *         The payload to parse.
     *
     * Returns:
     *     object:
     *     The returned attributes.
     */
    parse(rsp) {
        return _.extend(this._parseDiffContext(rsp),
                        RB.ReviewablePage.prototype.parse.call(this, rsp));
    },

    /**
     * Load a new diff from the server.
     *
     * Args:
     *     options (object):
     *         The options for the diff to load.
     *
 *     Option Args:
     *     page (number):
     *         The page number to load. Defaults to the first page.
     *
     *     revision (number):
     *         The base revision. If displaying an interdiff, this will be
     *         the first revision in the range.
     *
     *     interdiffRevision (number):
     *         The optional interdiff revision, representing the ending
     *         revision in a range.
     */
    loadDiffRevision(options={}) {
        const reviewRequestURL = this.get('reviewRequest').url();
        const queryArgs = [];

        if (options.revision) {
            queryArgs.push(`revision=${options.revision}`);
        }

        if (options.interdiffRevision) {
            queryArgs.push(`interdiff-revision=${options.interdiffRevision}`);
        }

        if (options.page && options.page !== 1) {
            queryArgs.push(`page=${options.page}`);
        }

        this.set('canDownloadDiff', !options.interdiffRevision);

        $.ajax(`${reviewRequestURL}diff-context/?${queryArgs.join('&')}`)
            .done(rsp => this.set(this._parseDiffContext(rsp.diff_context)));
    },

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
    _parseDiffContext(rsp) {
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

        return {
            numDiffs: rsp.num_diffs || 0,
        };
    },
});
