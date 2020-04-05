/**
 * The administration UI's main dashboard page.
 *
 * This displays all the widgets rendered on the dashboard, allowing users to
 * see important details about their install from one place.
 */
RB.Admin.DashboardPageView = RB.Admin.PageView.extend({
    events: {
        'click .js-action-remove-widget': '_onRemoveWidgetClicked',
    },

    /**
     * Initialize the page.
     */
    initialize() {
        RB.Admin.PageView.prototype.initialize.apply(this, arguments);

        this._widgetViews = {};
        this._widgetWidths = {};
        this._orderedWidgets = [];
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
        RB.Admin.PageView.prototype.renderPage.call(this);

        /* Set up the main dashboard widgets area. */
        this._$dashboardView = this.$('#admin-dashboard');
        this._$widgetsContainer = this._$dashboardView.find(
            '.rb-c-admin-widgets');
        this._$widgetsMain = this._$widgetsContainer.children(
            '.rb-c-admin-widgets__main');
        this._$widgets = this._$widgetsMain.children('.rb-c-admin-widget');

        const $sizerGutter = this._$widgetsContainer.children(
            '.rb-c-admin-widgets__sizer-gutter');
        const $sizerColumn = this._$widgetsContainer.children(
            '.rb-c-admin-widgets__sizer-column');

        this._masonry = new Masonry(this._$widgetsMain[0], {
            columnWidth: $sizerColumn[0],
            gutter: $sizerGutter[0],
            transitionDuration: 0,
            initLayout: false,
        });

        /* Show a banner detailing the support coverage for the server. */
        const supportData = this.model.get('supportData');

        if (supportData) {
            const supportBanner = new RB.SupportBannerView({
                el: $('#support-banner'),
                supportData: this.model.get('supportData'),
            });
            supportBanner.render();
        }

        this._loadWidgets();

        this._masonry.on('layoutComplete', this._onLayoutComplete.bind(this));

        /* Now that everything is in place, show the dashboard. */
        this._$dashboardView.css('visibility', 'visible');
    },

    /**
     * Load all widgets for the view.
     *
     * The widgets will be loaded based on the data passed to the model,
     * and will then be added to Masonry in order of largest to smallest
     * widget.
     */
    _loadWidgets() {
        const sortableWidgets = [];
        let index = 0;

        /* Render all the widgets. */
        this.model.loadWidgets(widgetOptions => {
            const widgetModel = widgetOptions.widgetModel;
            const widgetView = new widgetOptions.ViewType(_.defaults(
                {
                    el: $(`#${widgetOptions.domID}`),
                    model: widgetModel,
                },
                widgetOptions.viewOptions));

            widgetView.$el.addClass('js-masonry-item');
            widgetView.render();

            this.listenTo(widgetView, 'sizeChanged',
                          () => this._onWidgetSizeChanged(widgetModel.id,
                                                          widgetView.$el));

            const widgetEl = widgetView.el;
            const width = widgetEl.offsetWidth;

            this._widgetViews[widgetModel.id] = widgetView;
            this._widgetWidths[widgetModel.id] = width;
            sortableWidgets.push({
                el: widgetEl,
                index: index,
                isFullWidth: widgetView.$el.hasClass('-is-full-size'),
                width: width,
            });
        });

        /*
         * Force a specific sort order for the widgets to ensure the most
         * compact layout, ideally keeping everything on screen.
         *
         * We require a stable order (widgets of the same size should be in a
         * predictable order), and we have to account for full-width widgets,
         * so our comparator is a little bit more complex. We use the
         * following rules:
         *
         * 1) Full-size widgets are positioned at the top.
         * 2) Column-based widgets are then ordered from largest to smallest.
         * 3) Any widgets of the same size are sorted according to their
         *    registration index.
         */
        sortableWidgets.sort((a, b) => {
            if (a.isFullWidth && !b.isFullWidth) {
                return -1;
            } else if (!a.isFullWidth && b.isFullWidth) {
                return 1;
            } else if (!a.isFullWidth && !b.isFullWidth &&
                       a.width !== b.width) {
                if (a.width > b.width) {
                    return -1;
                } else if (a.width < b.width) {
                    return 1;
                }
            }

            /* The widths are equal. Keep the widgets in index order. */
            return a.index - b.index;
        });

        this._masonry.items = [];
        this._masonry.addItems(_.pluck(sortableWidgets, 'el'));
        this._masonry.layout();
    },

    /**
     * Handle a completed widget re-layout.
     *
     * This will go through all the widgets and determine if any have changed
     * their sizes (widths). If so, their
     * :js:func:`RB.Admin.WidgetView.updateSize` method will be called.
     */
    _onLayoutComplete() {
        this.model.widgets.each(widget => {
            const widgetView = this._widgetViews[widget.id];
            const newWidth = widgetView.$el.width();

            if (newWidth !== this._widgetWidths[widget.id]) {
                widgetView.updateSize();
                this._widgetWidths[widget.id] = newWidth;
            }
        });
    },

    /**
     * Handle changes to widget sizes.
     *
     * This is called in response to the ``sizeChanged`` events on widgets. If
     * the size of the widget has actually changed, this will record the new
     * width and then update the positions of widgets accordingly.
     *
     * Args:
     *     widgetID (string):
     *         The ID of the widget that changed size.
     *
     *     $widget (jQuery):
     *         The widget's jQuery-wrapped element.
     */
    _onWidgetSizeChanged(widgetID, $widget) {
        const newWidth = $widget.width();

        if (newWidth !== this._widgetWidths[widgetID]) {
            this._widgetWidths[widgetID] = newWidth;
            this._masonry.layout();
        }
    },
});
