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
        'click .js-action-submit': '_onCloseCompletedClicked',
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
                close_submitted_text: gettext('<b>Close</b> Completed'),
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
     * Handler for when the Close Completed action is clicked.
     *
     * This will confirm that the user wants to close the selected
     * review requests. Once they confirm, the review requests will
     * be closed.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the callback.
     */
    _onCloseCompletedClicked(ev) {
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
    async _closeReviewRequests(closeType) {
        try {
            const confirmed = await this._confirmClose();

            if (confirmed) {
                const results = await this.model.closeReviewRequests({
                    closeType: closeType,
                });
                this._showCloseResults(results.successes, results.failures);
            }
        } catch (err) {
            alert(_`An error occurred when attempting to close review requests: ${err}`);
        }
    },

    /**
     * Shows the results of the close operation in a dialog.
     *
     * This will say how many review requests have been closed successfully,
     * and will also list the number that have failed (due to access
     * permissions or other errors).
     *
     * Args:
     *     successes (int):
     *         Number of successfully closed review requests.
     *
     *     failures (int):
     *         Number of unsuccessfully closed review requests.
     */
    _showCloseResults(successes, failures) {
        const $dlg = $('<div/>')
            .append($('<p/>')
                .text(interpolate(
                    ngettext('%s review request has been closed.',
                             '%s review requests have been closed.',
                             successes),
                    [successes])));

        if (failures > 0) {
            $dlg
                .append($('<p/>').text(
                    interpolate(
                        ngettext('%s review request could not be closed.',
                                 '%s review requests could not be closed.',
                                 failures),
                        [failures])))
                .append($('<p/>').text(
                    _`You may not have permission to close them.`));
        }

        $dlg
            .modalBox({
                title: _`Close review requests`,
                buttons: [
                    $('<input type="button"/>').val(_`Close`),
                ],
            })
            .on('close', () => $dlg.modalBox('destroy'));
    },

    /**
     * Prompt the user for confirmation before closing review requests.
     *
     * If the user confirms, the review requests will be closed.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves to true if the close was confirmed, or
     *     false if the close was cancelled.
     */
    _confirmClose: function() {
        return new Promise((resolve, reject) => {
            const $dialog = $('<div/>')
                .append($('<p/>')
                    .text(_`If these review requests have unpublished drafts, they will be discarded.`))
                .append($('<p/>')
                    .text(_`Are you sure you want to close these review requests?`))
                .modalBox({
                    title: _`Close review requests`,
                    buttons: [
                        $('<input type="button"/>')
                            .val(_`Cancel`)
                            .click(() => resolve(false)),

                        $('<input type="button"/>')
                            .val(_`Close Review Requests`)
                            .click(() => resolve(true)),
                    ],
                })
                .on('close', () => {
                    $dialog.modalBox('destroy');
                    resolve(false);
                });
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

        this.model.updateVisibility('archive');
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

        this.model.updateVisibility('unarchive');
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

        const $dialog = $('<div/>')
            .append($('<p/>')
                .text(_`Are you sure you want to mute these review requests?`))
            .modalBox({
                title: _`Mute review requests`,
                buttons: [
                    $('<input type="button"/>')
                        .val(_`Cancel`),

                    $('<input type="button"/>')
                        .val(_`Mute Review Requests`)
                        .click(() => this.model.updateVisibility('mute')),
                ],
            })
            .on('close', () => $dialog.modalBox('destroy'));
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

        this.model.updateVisibility('unarchive');
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
