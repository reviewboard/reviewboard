/*
 * Manages the UI for the page containing a main datagrid.
 *
 * This renders the datagrid, handles events, and allows for multi-row
 * actions.
 */
RB.DatagridPageView = Backbone.View.extend({
    RELOAD_INTERVAL_MS: 5 * 60 * 1000,

    /* The View class to use for an actions menu, if any. */
    actionsViewType: null,

    events: {
        'change tbody input[data-checkbox-name=select]': '_onRowSelected',
        'reloaded .datagrid-wrapper': '_setupDatagrid'
    },

    /*
     * Initializes the datagrid page.
     */
    initialize: function(options) {
        options = options || {};

        this.periodicReload = !!options.periodicReload;

        this._bottomSpacing = null;
        this._reloadTimer = null;
        this._datagrid = null;
        this._$wrapper = null;
        this._$datagridBody = null;
        this._$datagridBodyContainer = null;
        this._$window = null;
        this._menuShown = false;
        this._origActionsLeft = null;
    },

    /*
     * Renders the datagrid page view, and begins listening for events.
     */
    render: function() {
        this._$window = $(window);

        if (this.actionsViewType) {
            this._setupActionsView();
        }

        this.listenTo(this.model, 'refresh', function() {
            this._reload(false);
        });

        this._setupDatagrid();

        if (this.periodicReload) {
            this._startReloadTimer();
        }

        this._$window.resize(_.bind(this._updateSize, this));

        return this;
    },

    /*
     * Sets up the actions pane view.
     */
    _setupActionsView: function() {
        this._actionsView = new this.actionsViewType({
            model: this.model,
            datagridView: this
        });
        this._actionsView.$el.addClass('datagrid-actions');
        this._actionsView.render();

        this.listenTo(this.model, 'change:count', function(model, count) {
            var showMenu = (count > 0);

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

    /*
     * Sets up parts of the datagrid.
     *
     * This will reference elements inside the datagrid and set up UI.
     * This is called when first rendering the datagrid, and any time
     * the datagrid is reloaded from the server.
     */
    _setupDatagrid: function() {
        this._$wrapper = this.$('#content_container');
        this._$datagrid = this._$wrapper.find('.datagrid-wrapper');
        this._datagrid = this._$datagrid.data('datagrid');
        this._$main = this._$wrapper.find('.datagrid-main');
        this._$sidebarItems = this.$('.page-sidebar-items');

        if (this._actionsView) {
            this._$actionsContainer = $('<div/>')
                .addClass('datagrid-actions-container')
                .append(this._actionsView.$el)
                .appendTo($('#page_sidebar'));

            this._actionsView.delegateEvents();
        }

        this.$('time.timesince').timesince();
        this.$('.user').user_infobox();
        this.$('.bugs').find('a').bug_infobox();

        this.model.clearSelection();

        _.each(this.$('input[data-checkbox-name=select]:checked'),
               function(checkbox) {
            this.model.select($(checkbox).data('object-id'));
        }, this);

        this._updateSize();

        if (RB.UserSession.instance.get('authenticated')) {
            this._starManager = new RB.StarManagerView({
                model: new RB.StarManager(),
                el: this._$main,
                datagridMode: true
            });
        }

        this._$datagrid.on('reloaded', _.bind(this._setupDatagrid, this));
    },

    /*
     * Shows the actions pane.
     */
    _showActions: function() {
        var $actionsViewEl = this._actionsView.$el;

        if (this._origActionsLeft === null) {
            this._origActionsLeft = $actionsViewEl.css('left');
        }

        this._$sidebarItems.fadeOut('fast');
        this._$actionsContainer.show();
        $actionsViewEl
            .css('left', $actionsViewEl.outerWidth())
            .show()
            .animate({
                left: this._origActionsLeft
            });
    },

    /*
     * Hides the actions pane.
     */
    _hideActions: function() {
        var $actionsViewEl = this._actionsView.$el;

        this._$sidebarItems.fadeIn('slow');
        $actionsViewEl
            .animate({
                left: $actionsViewEl.outerWidth()
            }, {
                complete: _.bind(function() {
                    $actionsViewEl.hide();
                    this._$actionsContainer.hide();
                }, this)
            });
    },

    /*
     * Updates the size of this view.
     *
     * This will set the height of the view to take up the full height
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
     * Returns the spacing below the datagrid.
     *
     * This is used to consider padding when setting the height of the view.
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
     * Starts the reload timer, if it's not already running.
     */
    _startReloadTimer: function() {
        if (!this._reloadTimer) {
            this._reloadTimer = setInterval(_.bind(this._reload, this),
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
     * Reloads the datagrid contents.
     *
     * This may be called periodically to reload the contents of the
     * datagrid, if specified by the subclass.
     */
    _reload: function(periodicReload) {
        var $editCols = this.$('.edit-columns');

        if (periodicReload === false) {
            this._stopReloadTimer();
        }

        this.model.clearSelection();

        $editCols
            .width($editCols.width() - $editCols.getExtents('b', 'lr'))
            .html('<span class="fa fa-spinner fa-pulse"></span>');

        this._$wrapper.load(window.location + ' #content_container',
                            _.bind(function() {
            this.$('.datagrid-wrapper').datagrid();

            this._setupDatagrid();

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
            objectID = $checkbox.data('object-id');

        if ($checkbox.prop('checked')) {
            this.model.select(objectID);
        } else {
            this.model.unselect(objectID);
        }
    }
});
