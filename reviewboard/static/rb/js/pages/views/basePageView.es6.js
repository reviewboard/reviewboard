/**
 * Base class for the views for pages.
 *
 * This is responsible for setting up and handling the page's UI, including
 * the page header, mobile mode handling, and sidebars. It also provides some
 * utilities for setting up common UI elements.
 *
 * The page will respect the ``-has-sidebar`` and ``-is-content-full-page``
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
     *
     * Args:
     *     options (object, optional):
     *         Options for the page.
     *
     * Option Args:
     *     $body (jQuery, optional):
     *         The body element. This is useful for unit tests.
     *
     *     $headerBar (jQuery, optional):
     *         The header bar element. This is useful for unit tests.
     *
     *     $pageContainer (jQuery, optional):
     *         The page container element. This is useful for unit tests.
     *
     *     $pageContent (jQuery, optional):
     *         The page content element. This is useful for unit tests.
     *
     *     $pageSidebar (jQuery, optional):
     *         The page sidebar element. This is useful for unit tests.
     */
    initialize(options={}) {
        this.options = options;

        this.$window = $(window);
        this.$pageContainer = null;
        this.$pageContent = null;
        this.$mainSidebar = null;
        this._$pageSidebar = null;
        this._$mainSidebarPane = null;

        this.hasSidebar = null;
        this.isFullPage = null;
        this.inMobileMode = null;
        this.isPageRendered = false;

        this.drawer = null;
        this.headerView = null;
    },

    /**
     * Remove the page from the DOM and disable event handling.
     */
    remove() {
        if (this.$window) {
            this.$window.off('resize.rbPageView');
        }

        if (this.headerView) {
            this.headerView.remove();
        }

        Backbone.View.prototype.remove.call(this);
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
        const options = this.options;
        const $body = options.$body || $(document.body);

        this.$pageContainer = options.$pageContainer || $('#page-container');
        this.$pageContent = options.$pageContent || $('#content');
        this._$pageSidebar = options.$pageSidebar || $('#page-sidebar');
        this._$pageSidebarPanes = this._$pageSidebar.children(
            '.rb-c-page-sidebar__panes');
        this._$mainSidebarPane = this._$pageSidebarPanes.children(
            '.rb-c-page-sidebar__pane.-is-shown');
        this.$mainSidebar = this._$mainSidebarPane.children(
            '.rb-c-page-sidebar__pane-content');

        this.headerView = new RB.HeaderView({
            el: options.$headerBar || $('#headerbar'),
            $body: $body,
            $pageSidebar: this._$pageSidebar,
        });
        this.headerView.render();

        this.hasSidebar = $body.hasClass('-has-sidebar') ||
                          $body.hasClass('has-sidebar');
        this.isFullPage = $body.hasClass('-is-content-full-page') ||
                          $body.hasClass('full-page-content');
        this.inMobileMode = this.headerView.inMobileMode;

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

        this.$window.on('resize.rbPageView',
                        _.throttle(() => this._updateSize(),
                                   this.windowResizeThrottleMS));
        this.listenTo(this.headerView, 'mobileModeChanged',
                      this._onMobileModeChanged);
        this._onMobileModeChanged(this.inMobileMode);

        this.isPageRendered = true;

        return this;
    },

    /**
     * Set a drawer that can be shown over the sidebar.
     *
     * This is used by a page to set a drawer that should be displayed.
     * Drawers are shown over the sidebar area in desktop mode, or docked to
     * the bottom of the screen in mobile mode.
     *
     * Only one drawer can be set per page. Drawers also require a page with
     * sidebars enabled.
     *
     * Callers must instantiate the drawer but should not render it or
     * add it to the DOM.
     *
     * Args:
     *     drawer (RB.Drawer):
     *         The drawer to set.
     */
    setDrawer(drawer) {
        console.assert(
            this.drawer === null,
            'A drawer has already been set up for this page.');
        console.assert(
            this.hasSidebar,
            'Drawers can only be set up on pages with a sidebar.');

        this.drawer = drawer;
        drawer.render();
        this._reparentDrawer();

        this.listenTo(drawer, 'visibilityChanged', this._updateSize);
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
     * Resize an element to take the full height of a parent container.
     *
     * By default, this will size the element to the height of the main
     * page container. A specific parent can be specified for more specific
     * use cases.
     *
     * Args:
     *     $el (jQuery):
     *         The jQuery-wrapped element to resize.
     *
     *     $parent (jQuery, optional):
     *         The specific jQuery-wrapped parent element to base the size on.
     */
    resizeElementForFullHeight($el, $parent) {
        if ($parent === undefined) {
            $parent = this.$pageContainer;
        }

        $el.outerHeight($parent.height() - $el.position().top);
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
     */
    onResize() {
    },

    /**
     * Handle mobile mode changes.
     *
     * This will be called whenever the page goes between mobile/desktop
     * mode, allowing subclasses to adjust any UI elements as appropriate.
     *
     * Args:
     *     inMobileMode (bool):
     *         Whether the UI is now in mobile mode. This will be the same
     *         value as :js:attr:`inMobileMode`, and is just provided for
     *         convenience.
     */
    onMobileModeChanged(inMobileMode) {
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
        let sidebarHeight = null;

        if (this.isFullPage) {
            pageContainerHeight = windowHeight -
                                  this.$pageContainer.offset().top;
        }

        if (this.inMobileMode) {
            if (pageContainerHeight !== null &&
                this.drawer !== null &&
                this.drawer.isVisible) {
                /*
                 * If we're constraining the page container's height, and
                 * there's a drawer present, reduce the page container's
                 * height by the drawer size, so we don't make some content
                 * inaccessible due to an overlap.
                 */
                pageContainerHeight -= this.drawer.$el.outerHeight();
            }
        } else {
            if (pageContainerHeight !== null) {
                /*
                 * If we're constraining the page container's height,
                 * constrain the sidebar's as well.
                 */
                sidebarHeight = windowHeight - this._$pageSidebar.offset().top;
            }
        }

        if (pageContainerHeight === null) {
            this.$pageContainer.css('height', '');
        } else {
            this.$pageContainer.outerHeight(pageContainerHeight);
        }

        if (sidebarHeight === null) {
            this._$pageSidebar.css('height', '');
        } else {
            this._$pageSidebar.outerHeight(sidebarHeight);
        }

        this.onResize();
    },

    /**
     * Set the new parent for the drawer.
     *
     * In mobile mode, this will place the drawer within the main
     * ``#container``, right before the sidebar, allowing it to appear docked
     * along the bottom of the page.
     *
     * In desktop mode, this will place the drawer within the sidebar area,
     * ensuring that it overlaps it properly.
     */
    _reparentDrawer() {
        const $el = this.drawer.$el
            .detach();

        if (this.inMobileMode) {
            $el.insertBefore(this._$pageSidebar);
        } else {
            $el.appendTo(this._$pageSidebarPanes);
        }
    },

    /**
     * Handle a transition between mobile and desktop mode.
     *
     * This will set the :js:attr:`inMobileMode` flag and trigger the
     * ``inMobileModeChanged`` event, so that pages can listen and update
     * their layout as appropriate.
     *
     * It will also update the size and reparent the drawer.
     *
     * Args:
     *     inMobileMode (boolean):
     *         Whether the page shell is in mobile mode.
     */
    _onMobileModeChanged(inMobileMode) {
        this.inMobileMode = inMobileMode;

        this._updateSize();

        if (this.drawer !== null) {
            this._reparentDrawer();
        }

        this.onMobileModeChanged(this.inMobileMode);
        this.trigger('inMobileModeChanged', this.inMobileMode);
    },
});
