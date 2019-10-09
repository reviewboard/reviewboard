(function() {


/**
 * Displays and invokes actions for one or more review requests.
 *
 * This presents available actions to the user that can be performed
 * across one or more selected review requests in the dashboard.
 * The actions will appear in a layer above the sidebar.
 */
const DashboardActionsView = Backbone.View.extend({
    template: _.template(dedent`
        <p class="rb-c-drawer__summary"></p>
        <% if (!read_only) { %>
         <div class="rb-c-drawer__actions">
          <ul class="rb-c-drawer__action-group">
           <li class="rb-c-drawer__action js-action-discard">
            <%= close_discarded_text %>
           </li>
           <li class="rb-c-drawer__action js-action-submit">
            <%= close_submitted_text %>
           </li>
          </ul>
          <ul class="rb-c-drawer__action-group">
           <li class="rb-c-drawer__action js-action-archive">
            <%= archive_text %>
           </li>
           <% if (show_archived) { %>
            <li class="rb-c-drawer__action
                       js-action-unarchive">
             <%= unarchive_text %>
            </li>
           <% } %>
          </ul>
          <ul class="rb-c-drawer__action-group">
           <li class="rb-c-drawer__action js-action-mute">
            <%= mute_text %></a></li>
           </li>
           <% if (show_archived) { %>
            <li class="rb-c-drawer__action js-action-unmute">
             <%= unmute_text %>
            </li>
           <% } %>
          </ul>
         </div>
        <% } %>
    `),

    events: {
        'click .js-action-discard': '_onCloseDiscardedClicked',
        'click .js-action-submit': '_onCloseSubmittedClicked',
        'click .js-action-archive': '_onArchiveClicked',
        'click .js-action-unarchive': '_onUnarchiveClicked',
        'click .js-action-mute': '_onMuteClicked',
        'click .js-action-unmute': '_onUnmuteClicked',
    },

    /**
     * Render the actions pane.
     *
     * Returns:
     *     DashboardActionsView:
     *     This object, for chaining.
     */
    render() {
        const show_archived = (this.model.get('data') || {}).show_archived;

        this.$el
            .html(this.template({
                close_discarded_text: gettext('<b>Close</b> Discarded'),
                close_submitted_text: gettext('<b>Close</b> Submitted'),
                archive_text: gettext('<b>Archive</b>'),
                mute_text: gettext('<b>Mute</b>'),
                read_only: RB.UserSession.instance.get('readOnly'),
                unarchive_text: gettext('<b>Unarchive</b>'),
                unmute_text: gettext('<b>Unmute</b>'),
                show_archived: show_archived,
            }));

        const $summary = this.$('.rb-c-drawer__summary');

        this.listenTo(this.model, 'change:count', (model, count) => {
            $summary.text(interpolate(
                ngettext('%s review request selected',
                         '%s review requests selected',
                         count),
                [count]));
        });

        return this;
    },

    /**
     * Handler for when the Close Discarded action is clicked.
     *
     * This will confirm that the user wants to close the selected
     * review requests. Once they confirm, the review requests will
     * be closed.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the callback.
     */
    _onCloseDiscardedClicked(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        this._closeReviewRequests(RB.ReviewRequest.CLOSE_DISCARDED);
    },

    /**
     * Handler for when the Close Submitted action is clicked.
     *
     * This will confirm that the user wants to close the selected
     * review requests. Once they confirm, the review requests will
     * be closed.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the callback.
     */
    _onCloseSubmittedClicked(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        this._closeReviewRequests(RB.ReviewRequest.CLOSE_SUBMITTED);
    },

    /**
     * Common code for confirming and closing review requests.
     *
     * This will confirm that the user wants to close the selected
     * review requests. Once they confirm, the review requests will
     * be closed.
     *
     * Args:
     *     closeType (string):
     *         The close type to use.
     */
    _closeReviewRequests(closeType) {
        this._confirmClose(() => {
            this.model.closeReviewRequests({
                closeType: closeType,
                onDone: this._showCloseResults.bind(this),
            });
        });
    },

    /**
     * Shows the results of the close operation in a dialog.
     *
     * This will say how many review requests have been closed successfully,
     * and will also list the number that have failed (due to access
     * permissions or other errors).
     *
     * Args:
     *     successes (Array):
     *         Array of successfully closed review requests.
     *
     *     failures (Array):
     *         Array of unsuccessfully closed review requests.
     */
    _showCloseResults(successes, failures) {
        const numSuccesses = successes.length;
        const numFailures = failures.length;
        const $dlg = $('<div/>')
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
                $('<input type="button"/>').val(gettext('Thanks!')),
            ],
        });
    },

    /**
     * Prompt the user for confirmation before closing review requests.
     *
     * If the user confirms, the review requests will be closed.
     *
     * Args:
     *     onConfirmed (function):
     *         Function to call after the user confirms.
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
                        .click(onConfirmed.bind(this)),
                ],
            });
    },

    /**
     * Handler for when the Archive action is clicked.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the callback.
     */
    _onArchiveClicked(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const collection = RB.UserSession.instance.archivedReviewRequests;
        this._updateVisibility(collection.addImmediately.bind(collection));
    },

    /**
     * Handler for when the Unarchive action is clicked.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the callback.
     */
    _onUnarchiveClicked(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const collection = RB.UserSession.instance.archivedReviewRequests;
        this._updateVisibility(collection.removeImmediately.bind(collection));
    },

    /**
     * Handler for when the Mute action is clicked.
     *
     * This will confirm that the user wants to mute the selected review
     * requests. Once they confirm, the review requests will be archived.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the callback.
     */
    _onMuteClicked(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const collection = RB.UserSession.instance.mutedReviewRequests;
        const visibilityFunc = collection.addImmediately.bind(collection);

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
                        .click(this._updateVisibility.bind(
                            this, visibilityFunc)),
                ],
            });
    },

    /**
     * Handler for when the Unmute action is clicked.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the callback.
     */
    _onUnmuteClicked(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const collection = RB.UserSession.instance.mutedReviewRequests;

        this._updateVisibility(collection.removeImmediately.bind(collection));
    },

    /**
     * Common code for archiving/muting review requests.
     *
     * Args:
     *     visibilityFunc (function):
     *         Function to call to update the visibility of an individual
     *         review request.
     */
    _updateVisibility(visibilityFunc) {
        this.model.updateVisibility(visibilityFunc);
    },
});


/**
 * Manages the UI for the dashboard.
 *
 * This renders the dashboard, handles events, and allows for multi-row
 * actions (like closing review requests).
 */
RB.DashboardView = RB.DatagridPageView.extend({
    actionsViewType: DashboardActionsView,
});


})();
