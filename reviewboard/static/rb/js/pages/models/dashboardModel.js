/*
 * Models the dashboard and its operations.
 *
 * This will keep track of any selected review requests, and can
 * perform operations on them.
 */
RB.Dashboard = RB.DatagridPage.extend({
    rowObjectType: RB.ReviewRequest,

    /*
     * Closes all selected review requests.
     *
     * This will keep track of all the successes and failures and report
     * them back to the caller once completed.
     */
    closeReviewRequests: function(options) {
        function closeNext() {
            if (reviewRequests.length === 0) {
                this.selection.reset();
                this.trigger('refresh');
                options.onDone(successes, failures);
                return;
            }

            reviewRequest = reviewRequests.shift();

            reviewRequest.close({
                type: options.closeType,
                success: function() {
                    successes.push(reviewRequest);
                },
                error: function() {
                    failures.push(reviewRequest);
                },
                complete: _.bind(closeNext, this)
            });
        }

        var reviewRequests = this.selection.clone(),
            successes = [],
            failures = [];

        closeNext.call(this);
    }
});
