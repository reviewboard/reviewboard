/**
 * The model for the diff viewer page.
 *
 * This handles all attribute storage and diff context parsing needed to
 * display and update the diff viewer.
 *
 * Model Attributes:
 *     commentsHint (RB.DiffCommentsHint):
 *         The comments hint model.
 *
 *     files (RB.DiffFileCollection):
 *         The collection of files on the page.
 *
 *     numDiffs (number):
 *         The number of total diffs.
 *
 *     pagination (RB.Pagination):
 *         The pagination handler for the diff viewer.
 *
 *     revision (RB.DiffRevision):
 *         The current diff revision on the page.
 */
RB.DiffViewerPage = RB.ReviewablePage.extend({
    defaults: _.defaults({
        commentsHint: null,
        files: null,
        numDiffs: 1,
        pagination: null,
        revision: null,
    }, RB.ReviewablePage.prototype.defaults),

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
        return {
            commentsHint: new RB.DiffCommentsHint(rsp.comments_hint,
                                                  {parse: true}),
            files: new RB.DiffFileCollection(rsp.files, {parse: true}),
            numDiffs: rsp.num_diffs || 0,
            pagination: new RB.Pagination(rsp.pagination, {parse: true}),
            revision: new RB.DiffRevision(rsp.revision, {parse: true}),
        };
    },

    /**
     * Override for Model.set that properly updates the child objects.
     *
     * Because several of this model's properties are other backbone models, we
     * can't just call ``set(parse(...))`` because it would replace the models
     * entirely. If this is called as part of the initial construction, it will
     * just use the models created by :js:func:`parse`. Otherwise, it will
     * copy the new data into the child models' attributes.
     *
     * Args:
     *     attrs (object):
     *         The new attributes being set.
     *
     *     options (object):
     *         The options for the set.
     */
    set(attrs, options) {
        const toIgnore = {};
        const toSet = {};

        if (this.attributes.commentsHint && attrs.commentsHint) {
            this.attributes.commentsHint.set(attrs.commentsHint.attributes);
            toIgnore.commentsHint = true;
        }

        if (this.attributes.files && attrs.files) {
            this.attributes.files.set(attrs.files.models);
            this.attributes.files.trigger('update');
            toIgnore.files = true;
        }

        if (this.attributes.pagination && attrs.pagination) {
            this.attributes.pagination.set(attrs.pagination.attributes);
            toIgnore.pagination = true;
        }

        if (this.attributes.revision && attrs.revision) {
            this.attributes.revision.set(attrs.revision.attributes);
            toIgnore.revision = true;
        }

        /* Anything not explicitly handled above can be set. */
        for (let attr in attrs) {
            if (attrs.hasOwnProperty(attr) && !toIgnore[attr]) {
                toSet[attr] = attrs[attr];
            }
        }

        RB.ReviewablePage.prototype.set.call(this, toSet, options);
    },
});
