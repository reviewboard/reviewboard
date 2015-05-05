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
        var reviewRequests = this.selection.clone(),
            successes = [],
            failures = [];

        function closeNext() {
            var reviewRequest;

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

        closeNext.call(this);
    },

    /*
     * Update the visibility of the selected review requests.
     *
     * This expects to be passed in a properly bound function (either
     * addImmediately or removeImmediately) on either archivedReviewRequests or
     * mutedReviewRequests. This will keep track of all the successes and
     * failures, reporting them back to the caller.
     */
    updateVisibility: function(visibilityFunc) {
        var reviewRequests = this.selection.clone(),
            successes = [],
            failures = [];

        function hideNext() {
            var reviewRequest;

            if (reviewRequests.length === 0) {
                this.selection.reset();
                this.trigger('refresh');
                return;
            }

            reviewRequest = reviewRequests.shift();

            visibilityFunc(
                reviewRequest,
                {
                    success: function() {
                        successes.push(reviewRequest);
                        hideNext.call(this);
                    },
                    error: function() {
                        failures.push(reviewRequest);
                        hideNext.call(this);
                    }
                },
                this);
        }

        hideNext.call(this);
    }
});
