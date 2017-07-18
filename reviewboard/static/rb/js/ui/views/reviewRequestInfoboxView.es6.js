/**
 * An infobox for displaying information on review requests.
 */
RB.ReviewRequestInfoboxView = RB.BaseInfoboxView.extend({
    infoboxID: 'review-request-infobox',
});


$.fn.review_request_infobox = RB.InfoboxManagerView.createJQueryFn(
    RB.ReviewRequestInfoboxView);
