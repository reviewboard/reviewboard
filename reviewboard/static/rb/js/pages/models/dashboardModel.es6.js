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
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    closeReviewRequests(options) {
        const localSiteName = this.get('localSiteName');
        const reviewRequests = this.selection.clone();

        const closeTypeToOp = {
            [RB.ReviewRequest.CLOSE_SUBMITTED]: 'close',
            [RB.ReviewRequest.CLOSE_DISCARDED]: 'discard',
        };

        return new Promise((resolve, reject) => {
            RB.apiCall({
                prefix: localSiteName ? `s/${localSiteName}/` : null,
                url: `${SITE_ROOT}r/_batch/`,
                data: {
                    batch: JSON.stringify({
                        op: closeTypeToOp[options.closeType],
                        review_requests: reviewRequests.map(
                            reviewRequest => reviewRequest.get('id')),
                    }),
                },
                success: (rsp) => {
                    this.selection.reset();
                    this.trigger('refresh');

                    resolve({
                        successes: rsp.review_requests_closed,
                        failures: rsp.review_requests_not_closed,
                    });
                },
                error: xhr => {
                    const rsp = xhr.responseJSON;

                    if (rsp.stat) {
                        this.trigger('refresh');
                        resolve({
                            successes: rsp.review_requests_closed,
                            failures: rsp.review_requests_not_closed,
                        });
                    } else {
                        console.error('Failed to run close batch operation', xhr);
                        reject(xhr.statusText);
                    }
                },
            });
        });
    },

    /**
     * Update the visibility of the selected review requests.
     *
     * Args:
     *     visibility (string):
     *         The visibility state to set (one of "archive", "mute", or
     *         "unarchive").
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    updateVisibility(visibility) {
        const localSiteName = this.get('localSiteName');
        const reviewRequests = this.selection.clone();

        return new Promise((resolve, reject) => {
            RB.apiCall({
                prefix: localSiteName ? `s/${localSiteName}/` : null,
                url: `${SITE_ROOT}r/_batch/`,
                data: {
                    batch: JSON.stringify({
                        op: visibility,
                        review_requests: reviewRequests.map(
                            reviewRequest => reviewRequest.get('id')),
                    }),
                },
                success: rsp => {
                    this.selection.reset();
                    this.trigger('refresh');

                    resolve({
                    });
                },
                error: xhr => {
                    const rsp = xhr.responseJSON;

                    if (rsp.stat) {
                        this.trigger('refresh');
                        resolve({
                        });
                    } else {
                        console.error('Failed to run visibility batch operation', xhr);
                        reject(xhr.statusText);
                    }
                },
            });
        });
    },
});
