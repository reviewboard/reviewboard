(function() {


/*
 * Displays and invokes actions for one or more review requests.
 *
 * This presents available actions to the user that can be performed
 * across one or more selected review requests in the dashboard.
 * The actions will appear in a layer above the sidebar.
 */
var DashboardActionsView = Backbone.View.extend({
    template: _.template([
        '<div class="datagrid-actions-content">',
        ' <p class="count"></p>',
        ' <ul>',
        '  <li><a class="discard" href="#"><%= close_discarded_text %></li>',
        '  <li><a class="submit" href="#"><%= close_submitted_text %></li>',
        ' </ul>',
        '</div>'
    ].join('')),

    events: {
        'click .discard': '_onCloseDiscardedClicked',
        'click .submit': '_onCloseSubmittedClicked'
    },

    /*
     * Initializes the actions pane.
     */
    initialize: function() {
        this._$content = null;
        this._$count = null;
    },

    /*
     * Renders the actions pane.
     */
    render: function() {
        this.$el
            .hide()
            .html(this.template({
                close_discarded_text: gettext('<b>Close</b> Discarded'),
                close_submitted_text: gettext('<b>Close</b> Submitted')
            }));

        this._$content = this.$('.datagrid-actions-content');
        this._$count = this.$('.count');

        this.listenTo(this.model, 'change:count', function(model, count) {
            this._$count.text(interpolate(
                ngettext('%s review request selected',
                         '%s review requests selected',
                         count),
                [count]));
        });

        return this;
    },

    /*
     * Handler for when the Close Discarded action is clicked.
     *
     * This will confirm that the user wants to close the selected
     * review requests. Once they confirm, the review requests will
     * be closed.
     */
    _onCloseDiscardedClicked: function() {
        this._closeReviewRequests(RB.ReviewRequest.CLOSE_DISCARDED);

        return false;
    },

    /*
     * Handler for when the Close Submitted action is clicked.
     *
     * This will confirm that the user wants to close the selected
     * review requests. Once they confirm, the review requests will
     * be closed.
     */
    _onCloseSubmittedClicked: function() {
        this._closeReviewRequests(RB.ReviewRequest.CLOSE_SUBMITTED);

        return false;
    },

    /*
     * Common code for confirming and closing review requests.
     *
     * This will confirm that the user wants to close the selected
     * review requests. Once they confirm, the review requests will
     * be closed.
     */
    _closeReviewRequests: function(closeType) {
        this._confirmClose(function() {
            this.model.closeReviewRequests({
                closeType: closeType,
                onDone: _.bind(this._showCloseResults, this)
            });
        });
    },

    /*
     * Shows the results of the close operation in a dialog.
     *
     * This will say how many review requests have been closed successfully,
     * and will also list the number that have failed (due to access
     * permissions or other errors).
     */
    _showCloseResults: function(successes, failures) {
        var numSuccesses = successes.length,
            numFailures = failures.length,
            $dlg = $('<div/>')
                .append($('<p/>')
                    .text(interpolate(
                        ngettext('%s review request has been closed.',
                                 '%s review requests have been closed.',
                                 numSuccesses),
                        [numSuccesses])));

        if (numFailures > 0) {
            $dlg
                .append($('<p/>').text(
                    interpolate(
                        ngettext('%s review request could not be closed.',
                                 '%s review requests could not be closed.',
                                 numFailures),
                        [numFailures])))
                .append($('<p/>').text(
                    gettext('You may not have permission to close them.')));
        }

        $dlg.modalBox({
            title: gettext('Close review requests'),
            buttons: [
                $('<input type="button"/>').val(gettext('Thanks!'))
            ]
        });
    },

    /*
     * Prompts the user for confirmation before closing review requests.
     *
     * If the user confirms, the review requests will be closed.
     */
    _confirmClose: function(onConfirmed) {
        $('<div/>')
            .append($('<p/>')
                .text(gettext('If these review requests have unpublished drafts, they will be discarded.')))
            .append($('<p/>')
                .text(gettext('Are you sure you want to close these review requests?')))
            .modalBox({
                title: gettext('Close review requests'),
                buttons: [
                    $('<input type="button"/>')
                        .val(gettext('Cancel')),

                    $('<input type="button"/>')
                        .val(gettext('Close Review Requests'))
                        .click(_.bind(onConfirmed, this))
                ]
            });
    }
});


/*
 * Manages the UI for the dashboard.
 *
 * This renders the dashboard, handles events, and allows for multi-row
 * actions (like closing review requests).
 */
RB.DashboardView = RB.DatagridPageView.extend({
    actionsViewType: DashboardActionsView
});


})();
