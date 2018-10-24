(function() {


const parentModel = RB.ReviewRequestPage.StatusUpdatesEntry;


/**
 * An entry on the review request page for review request changes.
 *
 * This stores state needed for change descriptions, including the status
 * updates on the change.
 *
 * Model Attributes:
 *     commits (RB.DiffCommitCollection):
 *         The collection of both old and new commits for this change entry.
 *
 * See Also:
 *     :js:class:`RB.ReviewRequestPage.StatusUpdatesEntry`:
 *         For additional model attribtues.
 *
 */
RB.ReviewRequestPage.ChangeEntry = parentModel.extend({
    /**
     * Return the default attribute values.
     *
     * Returns:
     *     object:
     *     The default attribute values.
     */
    defaults() {
        return _.defaults({
            commits: null,
        }, parentModel.prototype.defaults.call(this));
    },

    /**
     * Parse attributes for the model.
     *
     * Args:
     *     attrs (object):
     *         The attributes provided when constructing the model
     *         instance.
     *
     * Returns:
     *     object:
     *     The resulting attributes used for the model instance.
     */
    parse(attrs) {
        const commits = attrs.commits
            ? new RB.DiffCommitCollection(attrs.commits, {parse: true})
            : null;

        return _.extend(
            parentModel.prototype.parse.call(this, attrs),
            {
                commits: commits,
            });
    },
});


})();
