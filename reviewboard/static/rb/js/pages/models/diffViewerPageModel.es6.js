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
RB.DiffViewerPageModel = RB.Page.extend({
    defaults: _.defaults({
        commentsHint: null,
        files: null,
        numDiffs: 1,
        pagination: null,
        revision: null,
    }, RB.Page.prototype.defaults),

    /**
     * Parse the data given to us by the server.
     *
     * Args:
     *     rsp (object):
     *         The payload to parse.
     *
     * Returns:
     *     object:
     *     The resulting attributes for the model.
     */
    parse(rsp) {
        return {
            commentsHint: new RB.DiffCommentsHint(rsp.comments_hint,
                                                  {parse: true}),
            files: new RB.DiffFileCollection(rsp.files, {parse: true}),
            numDiffs: rsp.num_diffs,
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
        const toSet = {
            numDiffs: attrs.numDiffs,
        };

        if (this.attributes.commentsHint) {
            this.attributes.commentsHint.set(
                attrs.commentsHint.attributes);
        } else {
            toSet.commentsHint = attrs.commentsHint;
        }

        if (this.attributes.files) {
            this.attributes.files.set(attrs.files.models);
            this.attributes.files.trigger('update');
        } else {
            toSet.files = attrs.files;
        }

        if (this.attributes.pagination) {
            this.attributes.pagination.set(attrs.pagination.attributes);
        } else {
            toSet.pagination = attrs.pagination;
        }

        if (this.attributes.revision) {
            this.attributes.revision.set(attrs.revision.attributes);
        } else {
            toSet.revision = attrs.revision;
        }

        RB.Page.prototype.set.call(this, toSet, options);
    },
});
