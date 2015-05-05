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
        '  <li><a class="discard" href="#"><%= close_discarded_text %></a></li>',
        '  <li><a class="submit" href="#"><%= close_submitted_text %></a></li>',
        '  <li>&nbsp;</li>',
        '  <li><a class="archive" href="#"><%= archive_text %></a></li>',
        '<% if (show_archived) { %>',
        '  <li><a class="unarchive" href="#"><%= unarchive_text %></a></li>',
        '<% } %>',
        '  <li>&nbsp;</li>',
        '  <li><a class="mute" href="#"><%= mute_text %></a></li>',
        '<% if (show_archived) { %>',
        '  <li><a class="unmute" href="#"><%= unmute_text %></a></li>',
        '<% } %>',
        ' </ul>',
        '</div>'
    ].join('')),

    events: {
        'click .discard': '_onCloseDiscardedClicked',
        'click .submit': '_onCloseSubmittedClicked',
        'click .archive': '_onArchiveClicked',
        'click .unarchive': '_onUnarchiveClicked',
        'click .mute': '_onMuteClicked',
        'click .unmute': '_onUnmuteClicked'
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
        var show_archived = (this.model.get('data') || {}).show_archived;

        this.$el
            .hide()
            .html(this.template({
                close_discarded_text: gettext('<b>Close</b> Discarded'),
                close_submitted_text: gettext('<b>Close</b> Submitted'),
                archive_text: gettext('<b>Archive</b>'),
                mute_text: gettext('<b>Mute</b>'),
                unarchive_text: gettext('<b>Unarchive</b>'),
                unmute_text: gettext('<b>Unmute</b>'),
                show_archived: show_archived
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
    },

    /*
     * Handler for when the Archive action is clicked.
     */
    _onArchiveClicked: function() {
        var collection = RB.UserSession.instance.archivedReviewRequests;

        this._updateVisibility(
            _.bind(collection.addImmediately, collection));

        return false;
    },

    /*
     * Handler for when the Unarchive action is clicked.
     */
    _onUnarchiveClicked: function() {
        var collection = RB.UserSession.instance.archivedReviewRequests;

        this._updateVisibility(
            _.bind(collection.removeImmediately, collection));

        return false;
    },

    /*
     * Handler for when the Mute action is clicked.
     *
     * This will confirm that the user wants to mute the selected review
     * requests. Once they confirm, the review requests will be archived.
     */
    _onMuteClicked: function() {
        var collection = RB.UserSession.instance.mutedReviewRequests,
            visibilityFunc = _.bind(collection.addImmediately, collection);

        $('<div/>')
            .append($('<p/>')
                .text(gettext('Are you sure you want to mute these review requests?')))
            .modalBox({
                title: gettext('Mute review requests'),
                buttons: [
                    $('<input type="button"/>')
                        .val(gettext('Cancel')),

                    $('<input type="button"/>')
                        .val(gettext('Mute Review Requests'))
                        .click(_.bind(this._updateVisibility, this,
                                      visibilityFunc))
                ]
            });

        return false;
    },

    /*
     * Handler for when the Unmute action is clicked.
     */
    _onUnmuteClicked: function() {
        var collection = RB.UserSession.instance.mutedReviewRequests;

        this._updateVisibility(
            _.bind(collection.removeImmediately, collection));

        return false;
    },

    /*
     * Common code for archiving/muting review requests.
     */
    _updateVisibility: function(visibilityFunc) {
        this.model.updateVisibility(visibilityFunc);
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
