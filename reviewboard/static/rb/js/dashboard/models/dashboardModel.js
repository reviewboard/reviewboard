/*
 * Models the dashboard and its operations.
 *
 * This will keep track of any selected review requests, and can
 * perform operations on them.
 */
RB.Dashboard = Backbone.Model.extend({
    defaults: {
        count: 0,
        localSiteName: null
    },

    /*
     * Initializes the model.
     */
    initialize: function() {
        this.selection = new Backbone.Collection([], {
            model: RB.ReviewRequest
        });

        this.listenTo(this.selection, 'add remove reset', function() {
            this.set('count', this.selection.length);
        });
    },

    /*
     * Adds a selected review request to be used for any actions.
     */
    select: function(id) {
        var localSiteName = this.get('localSiteName');

        this.selection.add({
            id: id,
            localSitePrefix: localSiteName ? 's/' + localSiteName + '/' : null
        });
    },

    /*
     * Removes a selected review request.
     */
    unselect: function(id) {
        this.selection.remove(this.selection.get(id));
    },

    /*
     * Clears the list of selected review requests.
     */
    clearSelection: function() {
        this.selection.reset();
    },

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
