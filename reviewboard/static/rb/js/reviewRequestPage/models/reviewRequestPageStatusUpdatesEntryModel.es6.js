/**
 * An entry on the review request page for status updates.
 *
 * This stores common state needed for an entry containing status updates
 * made on a review request.
 *
 * See :js:class:`RB.ReviewRequestPageStatusUpdatesEntry` for additional model
 * attributes.
 *
 * Model Attributes:
 *     diffCommentsData (Array):
 *         An array of data for comments made on diffs. Each entry is an
 *         array in the format of ``[comment_id, key]``, where the key is
 *         a value for internal use that indicates the filediff or
 *         interfilediff range to use for loading diff fragments.
 *
 *     reviews (Array):
 *         An array of objects representing attributes for reviews for the
 *         status updates.
 */
RB.ReviewRequestPageStatusUpdatesEntry = RB.ReviewRequestPageEntry.extend({
    defaults: _.defaults({
        diffCommentsData: [],
        reviews: [],
    }, RB.ReviewRequestPageEntry.prototype.defaults),

    /**
     * Parse attributes for the model.
     *
     * Args:
     *     attrs (object):
     *         The attributes provided when constructing the model instance.
     *
     * Returns:
     *     object:
     *     The resulting attributes used for the model instance.
     */
    parse(attrs) {
        const reviewRequest = attrs.reviewRequestEditor.get('reviewRequest');
        const reviewsData = attrs.reviewsData || [];
        const reviews = reviewsData.map(
            reviewData => reviewRequest.createReview(reviewData.id, {
                bodyBottom: reviewData.bodyBottom,
                bodyTop: reviewData.bodyTop,
                'public': reviewData.public,
                shipIt: reviewData.shipIt,
            }));

        return _.extend(
            RB.ReviewRequestPageEntry.prototype.parse.call(this, attrs),
            {
                diffCommentsData: attrs.diffCommentsData,
                reviews: reviews,
            });
    },
});
