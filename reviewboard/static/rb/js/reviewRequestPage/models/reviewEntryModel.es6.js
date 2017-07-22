/**
 * An entry on the review request page for reviews.
 *
 * This stores state needed for a review entry on a review request.
 *
 * See :js:class:`RB.ReviewRequestPage.Entry` for additional model attributes.
 *
 * Model Attributes:
 *     diffCommentsData (Array):
 *         An array of data for comments made on diffs. Each entry is an
 *         array in the format of ``[comment_id, key]``, where the key is
 *         a value for internal use that indicates the filediff or
 *         interfilediff range to use for loading diff fragments.
 *
 *     review (RB.Review):
 *         The review being represented by this entry.
 */
RB.ReviewRequestPage.ReviewEntry = RB.ReviewRequestPage.Entry.extend({
    defaults: _.defaults({
        diffCommentsData: [],
        review: null,
    }, RB.ReviewRequestPage.Entry.prototype.defaults),

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
        const reviewData = attrs.reviewData;

        return _.extend(
            RB.ReviewRequestPage.Entry.prototype.parse.call(this, attrs),
            {
                diffCommentsData: attrs.diffCommentsData,
                review: reviewRequest.createReview(reviewData.id, {
                    bodyBottom: reviewData.bodyBottom,
                    bodyTop: reviewData.bodyTop,
                    'public': reviewData.public,
                    shipIt: reviewData.shipIt,
                }),
            });
    },
});
