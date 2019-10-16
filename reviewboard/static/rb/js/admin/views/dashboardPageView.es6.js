/**
 * The administration UI's main dashboard page.
 *
 * This displays all the widgets rendered on the dashboard, allowing users to
 * see important details about their install from one place.
 */
RB.Admin.DashboardPageView = RB.PageView.extend({
    events: {
        'click .js-action-remove-widget': '_onRemoveWidgetClicked',
    },

    /**
     * Initialize the page.
     */
    initialize() {
        RB.PageView.prototype.initialize.apply(this, arguments);

        this._$dashboardView = null;
        this._$widgetsContainer = null;
        this._$widgetsMain = null;
        this._$widgets = null;
        this._masonry = null;
    },

    /**
     * Render the page.
     *
     * This will set up the support banner and the dashboard widgets.
     */
    renderPage() {
        /* Set up the main dashboard widgets area. */
        this._$dashboardView = this.$('#admin-dashboard');
        this._$widgetsContainer = this._$dashboardView.find(
            '.rb-c-admin-widgets');
        this._$widgetsMain = this._$widgetsContainer.children(
            '.rb-c-admin-widgets__main');

        this._$widgets = this._$widgetsMain.children('.rb-c-admin-widget')
            .each((i, el) => {
                $(el)
                    .addClass('js-masonry-item')
                    .trigger('widget-shown');
            });

        const $sizerGutter = this._$widgetsContainer.children(
            '.rb-c-admin-widgets__sizer-gutter');
        const $sizerColumn = this._$widgetsContainer.children(
            '.rb-c-admin-widgets__sizer-column');
        this._masonry = new Masonry(this._$widgetsMain[0], {
            columnWidth: $sizerColumn[0],
            itemSelector: '.js-masonry-item',
            gutter: $sizerGutter[0],
            transitionDuration: 0,
            initLayout: false,
        });

        /* Show a banner detailing the support coverage for the server. */
        const supportBanner = new RB.SupportBannerView({
            el: $('#support-banner'),
            supportData: this.model.get('supportData'),
        });
        supportBanner.render();

        this.$window.on('resize.rbAdminDashboard',
                        this._layoutWidgets.bind(this));
        this._layoutWidgets();

        /* Now that everything is in place, show the dashboard. */
        this._$dashboardView.css('visibility', 'visible');
    },

    /**
     * Force a re-layout of the widgets.
     */
    _layoutWidgets() {
        this._masonry.layout();
    },
});
