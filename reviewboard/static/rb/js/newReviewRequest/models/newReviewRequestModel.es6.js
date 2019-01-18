/**
 * Model data for :js:class:`RB.NewReviewRequestView`.
 *
 * Model Attributes:
 *     repositories (Array of RB.Repository):
 *         The active repositories which can be selected.
 */
RB.NewReviewRequest = Backbone.Model.extend({
    defaults() {
        return {
            repositories: [],
        };
    },
});
