/*
 * Displays and invokes actions for one or more review requests.
 *
 * This presents available actions to the user that can be performed
 * across one or more selected review requests in the dashboard.
 * The actions will appear in a layer above the sidebar.
 */
var DashboardActionsView = Backbone.View.extend({
    id: 'dashboard_actions',

    template: _.template([
        '<div id="dashboard_actions_content">',
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

        this._$content = this.$('#dashboard_actions_content');
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
     * Shows the actions pane.
     */
    show: function() {
        this.$el.fadeIn('fast');
    },

    /*
     * Hides the actions pane.
     */
    hide: function() {
        this.$el.fadeOut('fast');
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
RB.DashboardView = Backbone.View.extend({
    RELOAD_INTERVAL_MS: 5 * 60 * 1000,

    events: {
        'change tbody input[data-checkbox-name=select]': '_onRowSelected',
        'reloaded .datagrid-wrapper': '_setupDashboard'
    },

    /*
     * Initializes the dashboard view.
     */
    initialize: function() {
        this._bottomSpacing = null;
        this._reloadTimer = null;
        this._datagrid = null;
        this._$wrapper = null;
        this._$datagridBody = null;
        this._$datagridBodyContainer = null;
        this._$window = null;
    },

    /*
     * Renders the dashboard view, and begins listening for events.
     */
    render: function() {
        this._$window = $(window);

        this.listenTo(this.model, 'change:count', function(model, count) {
            if (count > 0) {
                this._actionsView.show();

                /*
                 * Don't reload the dashboard while the user is
                 * preparing any actions.
                 */
                this._stopReloadTimer();
            } else {
                this._actionsView.hide();
                this._startReloadTimer();
            }
        });

        this.listenTo(this.model, 'refresh', function() {
            this._reloadDashboard(false);
        });

        this._actionsView = new DashboardActionsView({
            model: this.model
        });
        this._actionsView.render();

        this._setupDashboard();
        this._startReloadTimer();

        this._$window.resize(_.bind(this._updateSize, this));

        return this;
    },

    /*
     * Sets up parts of the dashboard.
     *
     * This will reference elements inside the datagrid and set up UI.
     * This is called when first rendering the dashboard, and any time
     * the datagrid is reloaded from the server.
     */
    _setupDashboard: function() {
        this._$wrapper = this.$('#dashboard-wrapper');
        this._$datagrid = this._$wrapper.find('.datagrid-wrapper');
        this._datagrid = this._$datagrid.data('datagrid');
        this._$main = this._$wrapper.find('.datagrid-main');

        this._actionsView.$el.appendTo(this.$('#dashboard_sidebar'));
        this._actionsView.delegateEvents();

        this.$('time.timesince').timesince();
        this.$('.user').user_infobox();

        this.model.clearSelection();

        _.each(this.$('input[data-checkbox-name=select]:checked'),
               function(checkbox) {
            this.model.select($(checkbox).data('object-id'));
        }, this);

        this._updateSize();

        this._$datagrid.on('reloaded', _.bind(this._setupDashboard, this));
    },

    /*
     * Starts the reload timer, if it's not already running.
     */
    _startReloadTimer: function() {
        if (!this._reloadTimer) {
            this._reloadTimer = setInterval(_.bind(this._reloadDashboard, this),
                                            this.RELOAD_INTERVAL_MS);
        }
    },

    /*
     * Stops the reload timer, if it's running.
     */
    _stopReloadTimer: function() {
        if (this._reloadTimer) {
            window.clearInterval(this._reloadTimer);
            this._reloadTimer = null;
        }
    },

    /*
     * Updates the size of the dashboard.
     *
     * This will set the height of the dashboard to take up the full height
     * of the page, minus some padding.
     */
    _updateSize: function() {
        this.$el
            .show()
            .outerHeight(this._$window.height() - this.$el.offset().top -
                         this._getBottomSpacing());
        this._datagrid.resizeToFit();
    },

    /*
     * Returns the spacing below the dashboard's datagrid.
     *
     * This is used to consider padding when setting the height of the
     * dashboard.
     */
    _getBottomSpacing: function() {
        if (this._bottomSpacing === null) {
            this._bottomSpacing = 0;

            _.each(this.$el.parents(), function(parentEl) {
                this._bottomSpacing += $(parentEl).getExtents('bmp', 'b');
            }, this);
        }

        return this._bottomSpacing;
    },

    /*
     * Reloads the dashboard contents.
     *
     * This is called periodically to reload the contents of the
     * dashboard.
     */
    _reloadDashboard: function(periodicReload) {
        var $editCols = this.$('.edit-columns');

        if (periodicReload === false) {
            this._stopReloadTimer();
        }

        this.model.clearSelection();

        $editCols
            .width($editCols.width() - 1)  // Account for border
            .children('img')
                .attr({
                    src: STATIC_URLS['rb/images/spinner.gif'],
                    width: 'auto',
                    height: 'auto'
                });

        this._$wrapper.load(window.location + ' #dashboard-wrapper',
                            _.bind(function() {
            this.$('.datagrid-wrapper').datagrid();

            this._setupDashboard();

            if (periodicReload !== false) {
                this._startReloadTimer();
            }
        }, this));
    },

    /*
     * Handler for when a row is selected.
     *
     * Records the row for any actions the user may wish to invoke.
     */
    _onRowSelected: function(e) {
        var $checkbox = $(e.target),
            reviewRequestID = $checkbox.data('object-id');

        if ($checkbox.prop('checked')) {
            this.model.select(reviewRequestID);
        } else {
            this.model.unselect(reviewRequestID);
        }
    }
});
