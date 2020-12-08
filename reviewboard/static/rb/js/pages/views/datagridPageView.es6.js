/**
 * Manages the UI for the page containing a main datagrid.
 *
 * This renders the datagrid, handles events, and allows for multi-row
 * actions.
 */
RB.DatagridPageView = RB.PageView.extend({
    RELOAD_INTERVAL_MS: 5 * 60 * 1000,

    /* The View class to use for an actions menu, if any. */
    actionsViewType: null,

    events: {
        'change tbody input[data-checkbox-name=select]': '_onRowSelected',
        'reloaded .datagrid-wrapper': '_setupDatagrid',
    },

    /**
     * Initialize the datagrid page.
     *
     * Args:
     *     options (object, optional):
     *         Options for the view.
     *
     * Option Args:
     *     periodicReload (boolean):
     *         Whether to periodically reload the contents of the datagrid.
     */
    initialize(options={}) {
        RB.PageView.prototype.initialize.call(this, options);

        this.periodicReload = !!options.periodicReload;

        this._reloadTimer = null;
        this._datagrid = null;
        this._$wrapper = null;
        this._$datagridBody = null;
        this._$datagridBodyContainer = null;
        this._menuShown = false;
    },

    /**
     * Render the datagrid page view, and begins listening for events.
     */
    renderPage() {
        RB.InfoboxManagerView.getInstance().setPositioning(
            RB.ReviewRequestInfoboxView,
            {
                /*
                 * The order on the side matters. If the Summary column is
                 * on the left-hand side of the datagrid, and "l" is first,
                 * it can end up taking priority, even if "L" was a better
                 * fit (since, if the infobox would need to be pushed a bit
                 * to fit on screen, it will prefer "l"). If the column is on
                 * the right-hand side of the dashboard, it will prefer "l",
                 * given the room available (taking into account the sidebar).
                 *
                 * So "L" is a better priority for the common use, and "l"
                 * works well as a fallback.
                 */
                side: 'Ll',
                LDistance: 300,
                lDistance: 20,
                yOffset: -20,
            });

        if (this.actionsViewType) {
            this._setupActionsDrawer();
        }

        this.listenTo(this.model, 'refresh', () => this._reload(false));

        this._setupDatagrid();

        if (this.periodicReload) {
            this._startReloadTimer();
        }

        return this;
    },

    /**
     * Handle page resizes.
     *
     * This will update the datagrid to fit on the page after a resize.
     */
    onResize() {
        if (this._datagrid !== null) {
            this._datagrid.resizeToFit();
        }
    },

    /**
     * Set up the actions pane view.
     */
    _setupActionsDrawer() {
        const drawer = new RB.DrawerView();
        this.setDrawer(drawer);

        this._actionsView = new this.actionsViewType({
            model: this.model,
            datagridView: this,
        });
        this._actionsView.render().$el.appendTo(drawer.$content);

        this.listenTo(this.model, 'change:count', (model, count) => {
            const showMenu = (count > 0);

            if (showMenu === this._menuShown) {
                return;
            }

            if (showMenu) {
                this._showActions();

                /*
                 * Don't reload the datagrid while the user is
                 * preparing any actions.
                 */
                this._stopReloadTimer();
            } else {
                this._hideActions();

                if (this.periodicReload) {
                    this._startReloadTimer();
                }
            }

            this._menuShown = showMenu;
        });
    },

    /**
     * Set up parts of the datagrid.
     *
     * This will reference elements inside the datagrid and set up UI.
     * This is called when first rendering the datagrid, and any time
     * the datagrid is reloaded from the server.
     */
    _setupDatagrid() {
        this._$wrapper = this.$('#content_container');
        this._$datagrid = this._$wrapper.find('.datagrid-wrapper');
        this._datagrid = this._$datagrid.data('datagrid');
        this._$main = this._$wrapper.find('.datagrid-main');

        this.$('time.timesince').timesince();
        this.$('.user').user_infobox();
        this.$('.bugs').find('a').bug_infobox();
        this.$('.review-request-link').review_request_infobox();

        this.model.clearSelection();

        _.each(this.$('input[data-checkbox-name=select]:checked'),
               checkbox => this.model.select($(checkbox).data('object-id')));

        if (RB.UserSession.instance.get('authenticated')) {
            this._starManager = new RB.StarManagerView({
                model: new RB.StarManager(),
                el: this._$main,
                datagridMode: true,
            });
        }

        this._$datagrid
            .on('reloaded', this._setupDatagrid.bind(this))
            .on('datagridDisplayModeChanged',
                this._reselectBatchCheckboxes.bind(this));
        this._datagrid.resizeToFit();
    },

    /**
     * Re-select any checkboxes that are part of the current selection.
     *
     * When the datagrid transitions between mobile and desktop modes,
     * we use two different versions of the table, meaning two sets of
     * checkboxes. This function updates the checkbox selection based on the
     * currently selected items.
     */
    _reselectBatchCheckboxes() {
        const checkboxMap = {};

        this.$('input[data-checkbox-name=select]').each((idx, checkboxEl) => {
            if (checkboxEl.checked) {
                checkboxEl.checked = false;
            }

            checkboxMap[checkboxEl.dataset.objectId] = checkboxEl;
        });

        this.model.selection.each(selection => {
            checkboxMap[selection.id].checked = true;
        });
    },

    /**
     * Show the actions drawer.
     */
    _showActions() {
        this.drawer.show();
    },

    /**
     * Hide the actions drawer.
     */
    _hideActions() {
        this.drawer.hide();
    },

    /**
     * Start the reload timer, if it's not already running.
     */
    _startReloadTimer() {
        if (!this._reloadTimer) {
            this._reloadTimer = setInterval(this._reload.bind(this),
                                            this.RELOAD_INTERVAL_MS);
        }
    },

    /**
     * Stop the reload timer, if it's running.
     */
    _stopReloadTimer() {
        if (this._reloadTimer) {
            window.clearInterval(this._reloadTimer);
            this._reloadTimer = null;
        }
    },

    /**
     * Reload the datagrid contents.
     *
     * This may be called periodically to reload the contents of the
     * datagrid, if specified by the subclass.
     *
     * Args:
     *     periodicReload (boolean):
     *         Whether the datagrid should reload periodically.
     */
    _reload(periodicReload) {
        const $editCols = this.$('.edit-columns');

        if (periodicReload === false) {
            this._stopReloadTimer();
        }

        this.model.clearSelection();

        $editCols
            .width($editCols.width() - $editCols.getExtents('b', 'lr'))
            .html('<span class="fa fa-spinner fa-pulse"></span>');

        this._$wrapper.load(window.location + ' #content_container', () => {
            this.$('.datagrid-wrapper').datagrid();

            this._setupDatagrid();

            if (periodicReload !== false) {
                this._startReloadTimer();
            }
        });
    },

    /**
     * Handler for when a row is selected.
     *
     * Records the row for any actions the user may wish to invoke.
     *
     * Args:
     *     e (Event):
     *         The event that triggered the callback.
     */
    _onRowSelected(e) {
        const $checkbox = $(e.target);
        const objectID = $checkbox.data('object-id');

        if ($checkbox.prop('checked')) {
            this.model.select(objectID);
        } else {
            this.model.unselect(objectID);
        }
    },
});
