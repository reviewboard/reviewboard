/*
 * A view that lists a series of commits.
 *
 * This is intended to be used for creating new review requests from committed
 * revisions. The containing view can call setPending/cancelPending to ask an
 * individual commit to show a spinner.
 */
RB.CommitsView = RB.CollectionView.extend({
    className: 'commits',
    itemViewType: RB.CommitView,

    /*
     * Set a given commit "pending".
     *
     * This is used while creating a new review request, and will ask the
     * correct commit view to show a spinner.
     */
    setPending: function(commit) {
        _.each(this.views, function(view) {
            if (view.model === commit) {
                view.showProgress();
            } else {
                view.cancelProgress();
            }
        });
    },

    /*
     * Cancel the pending state on all commits.
     */
    cancelPending: function() {
        _.each(this.views, function(view) {
            view.cancelProgress();
        });
    }
});
