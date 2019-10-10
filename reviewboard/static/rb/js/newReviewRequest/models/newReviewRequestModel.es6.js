/**
 * Model data for :js:class:`RB.NewReviewRequestView`.
 *
 * Model Attributes:
 *     repositories (Backbone.Collection of RB.Repository):
 *         The active repositories which can be selected.
 */
RB.NewReviewRequest = RB.Page.extend({
    defaults() {
        return _.defaults(_.result(RB.Page.prototype.defaults), {
            repositories: null,
        });
    },

    /**
     * Parse the data needed for the New Review Request page.
     *
     * Args:
     *     rsp (Array):
     *         The data provided to the page from the server.
     *
     * Returns:
     *     object:
     *     The parsed data used to populate the attributes.
     */
    parse(rsp) {
        return _.extend(RB.Page.prototype.parse.call(this, rsp), {
            repositories: new Backbone.Collection(
                rsp.repositories,
                {
                    model: RB.Repository,
                }),
        });
    },
});
