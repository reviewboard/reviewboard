/**
 * An infobox for displaying information on review requests.
 */
RB.ReviewRequestInfoboxView = RB.BaseInfoboxView.extend({
    infoboxID: 'review-request-infobox',

    /**
     * Return the infobox contents URL.
     *
     * This will use the ``review-request-url`` data attribute if it exists on
     * the target, otherwise this will use the ``href`` argument.
     *
     * Version Added:
     *     8.0
     *
     * Args:
     *     $target (jQuery):
     *         The target element the infobox is being shown for.
     *
     * Returns:
     *     string:
     *     The URL for the contents of the infobox.
     */
    getURLForTarget($target) {
        /* Review summary columns will set review-request-url. */
        const url = $target.data('review-request-url') ||
                    $target.attr('href');

        return `${url}infobox/`;
    },
});


$.fn.review_request_infobox = RB.InfoboxManagerView.createJQueryFn(
    RB.ReviewRequestInfoboxView);
