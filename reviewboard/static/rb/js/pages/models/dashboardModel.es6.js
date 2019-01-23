/**
 * Models the dashboard and its operations.
 *
 * This will keep track of any selected review requests, and can
 * perform operations on them.
 */
RB.Dashboard = RB.DatagridPage.extend({
    rowObjectType: RB.ReviewRequest,

    /**
     * Close all selected review requests.
     *
     * This will keep track of all the successes and failures and report
     * them back to the caller once completed.
     *
     * Args:
     *     options (object):
     *         Options for the operation.
     *
     * Option Args:
     *     closeType (string):
     *         The close type to use (submitted or discarded).
     *
     *     onDone (function):
     *         A function to call when the operation is complete.
     */
    closeReviewRequests(options) {
        const reviewRequests = this.selection.clone();
        const successes = [];
        const failures = [];

        function closeNext() {
            if (reviewRequests.length === 0) {
                this.selection.reset();
                this.trigger('refresh');
                options.onDone(successes, failures);
                return;
            }

            const reviewRequest = reviewRequests.shift();

            reviewRequest.close({
                type: options.closeType,
                success: () => successes.push(reviewRequest),
                error: () => failures.push(reviewRequest),
                complete: closeNext.bind(this),
            });
        }

        closeNext.call(this);
    },

    /**
     * Update the visibility of the selected review requests.
     *
     * This expects to be passed in a properly bound function (either
     * addImmediately or removeImmediately) on either archivedReviewRequests or
     * mutedReviewRequests. This will keep track of all the successes and
     * failures, reporting them back to the caller.
     *
     * Args:
     *     visibilityFunc (function):
     *         The function to call for each review request.
     */
    updateVisibility(visibilityFunc) {
        const reviewRequests = this.selection.clone();
        const successes = [];
        const failures = [];

        function hideNext() {
            if (reviewRequests.length === 0) {
                this.selection.reset();
                this.trigger('refresh');
                return;
            }

            const reviewRequest = reviewRequests.shift();

            visibilityFunc(
                reviewRequest,
                {
                    success: () => {
                        successes.push(reviewRequest);
                        hideNext.call(this);
                    },
                    error: () => {
                        failures.push(reviewRequest);
                        hideNext.call(this);
                    },
                });
        }

        hideNext.call(this);
    },
});
