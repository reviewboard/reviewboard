/**
 * Base class for the views for pages.
 *
 * This is responsible for setting up and handling the page's UI, including
 * the page header, mobile mode handling, and sidebars. It also provides some
 * utilities for setting up common UI elements.
 *
 * The page will respect the ``-has-sidebar`` and ``-has-full-page-content``
 * CSS classes on the document ``<body>``. These will control the behavior
 * and layout of the page.
 *
 * This is intended for use by page views that are set by
 * :js:class:`RB.PageManager`.
 */
RB.PageView = Backbone.View.extend({
    /**
     * The maximum frequency at which resize events should be handled.
     *
     * Subclasses can override this if they need to respond to window
     * resizes at a faster or slower rate.
     */
    windowResizeThrottleMS: 100,

    /**
     * Initialize the page.
     */
    initialize() {
        this.$window = $(window);
        this.$pageContainer = $('#page-container');
        this.isFullPage = null;

        this._$pageSidebar = null;
        this._$mainSidebarPane = null;
        this._$mainSidebarContent = null;

        this._bottomSpacing = null;

        this.headerView = new RB.HeaderView({
            el: $('#headerbar'),
        });
    },

    /**
     * Render the page.
     *
     * Subclasses should not override this. Instead, they should override
     * :js:func:`RB.PageView.renderPage``.
     *
     * Returns:
     *     RB.PageView:
     *     This object, for chaining.
     */
    render() {
        this._$pageSidebar = $('#page-sidebar');
        this._$pageSidebarPanes = $('#page-sidebar-panes');
        this._$mainSidebarPane = $('#page-sidebar-main-pane');
        this._$mainSidebarContent = $('#page-sidebar-main-content');

        const $body = $(document.body);
        this.isFullPage = $body.hasClass('-has-full-page-content') ||
                          $body.hasClass('full-page-content');

        this.headerView.render();

        this.renderPage();

        if (this.isFullPage) {
            /*
             * On full-size pages, we hide the content and sidebar initially
             * (via CSS), so that we can properly position them before they're
             * first shown. Now that we've done that, make them visible.
             */
            this._$mainSidebarPane.show();
            this.$pageContainer.show();
        }

        this.$window.on('resize', _.throttle(this._updateSize.bind(this),
                                             this.windowResizeThrottleMS));
        this.listenTo(this.headerView, 'mobileModeChanged', this._updateSize);
        this._updateSize();

        return this;
    },

    /**
     * Render the page contents.
     *
     * This should be implemented by subclasses that need to render any
     * UI elements.
     */
    renderPage() {
    },

    /**
     * Handle page resizes.
     *
     * This will be called whenever the page's size (or the window size)
     * has changed, allowing subclasses to adjust any UI elements as
     * appropriate.
     *
     * In the case of window sizes, calls to this function will be throttled,
     * called no more frequently than the configured
     * :js:attr:`windowResizeThrottleMS`.
     *
     * Args:
     *     heights (object):
     *         The calculated heights. This will include:
     *
     *         ``window`` (number):
     *             The new window height.
     *
     *         ``pageContainer`` (number):
     *             The fixed page container height, if in full-page content
     *             mode. ``null`` if in standard mode.
     */
    onResize(heights) {
    },

    /**
     * Update the size of the page.
     *
     * This will be called in response to window resizes and certain other
     * events. It will calculate the appropriate size for the sidebar (if
     * on the page) and the page container (if in full-page content mode),
     * update any elements as appropriate, and then call
     * :js:func:`RB.PageView.onResize` so that subclasses can update their
     * elements.
     */
    _updateSize() {
        const windowHeight = this.$window.height();
        let pageContainerHeight = null;

        if (this.isFullPage) {
            pageContainerHeight = windowHeight -
                                  this.$pageContainer.offset().top -
                                  this._getBottomSpacing();
            this.$pageContainer.outerHeight(pageContainerHeight);
        }

        this._$pageSidebar.outerHeight(this.headerView.inMobileMode
                                       ? windowHeight
                                       : pageContainerHeight);

        this.onResize({
            window: windowHeight,
            pageContainer: pageContainerHeight,
        });
    },

    /**
     * Return the spacing below the datagrid.
     *
     * This is used to consider padding when setting the height of the view.
     *
     * Returns:
     *     number:
     *     The amount of spacing below the datagrid.
     */
    _getBottomSpacing() {
        if (this._bottomSpacing === null) {
            this._bottomSpacing = 0;

            _.each(this.$pageContainer.parents(), parentEl => {
                this._bottomSpacing += $(parentEl).getExtents('bmp', 'b');
            });
        }

        return this._bottomSpacing;
    },
});
