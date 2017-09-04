/**
 * The model for the diff viewer page.
 *
 * This handles all attribute storage and diff context parsing needed to
 * display and update the diff viewer.
 *
 * Model Attributes:
 *     numDiffs (number):
 *         The total number of diffs.
 */
RB.DiffViewerPage = RB.ReviewablePage.extend({
    defaults: _.defaults({
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
        return _.extend(this.parseDiffContext(rsp),
                        RB.ReviewablePage.prototype.parse.call(this, rsp));
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
    parseDiffContext(rsp) {
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
