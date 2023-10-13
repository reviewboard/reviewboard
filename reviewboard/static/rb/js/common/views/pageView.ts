/**
 * Base class for page views.
 */
import { BaseView, spina } from '@beanbag/spina';

import { ActionView } from '../actions/views/actionView';
import { ClientCommChannel } from '../models/commChannelModel';
import { Page } from '../models/pageModel';


export interface PageViewOptions {
    /** The body element to use when running unit tests. */
    $body?: JQuery;

    /** The header element to use when running unit tests. */
    $headerBar?: JQuery;

    /** The page container element to use when running unit tests. */
    $pageContainer?: JQuery;

    /** The page content element to use when running unit tests. */
    $pageContent?: JQuery;

    /** The page sidebar element to use when running unit tests. */
    $pageSidebar?: JQuery;
}


/**
 * Base class for page views.
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
@spina({
    prototypeAttrs: ['windowResizeThrottleMS'],
})
export class PageView<
    TModel extends Page = Page,
    TElement extends HTMLDivElement = HTMLDivElement,
    TExtraViewOptions extends PageViewOptions = PageViewOptions
> extends BaseView<TModel, TElement, TExtraViewOptions> {
    /**
     * The maximum frequency at which resize events should be handled.
     *
     * Subclasses can override this if they need to respond to window
     * resizes at a faster or slower rate.
     */
    static windowResizeThrottleMS = 100;

    /**********************
     * Instance variables *
     **********************/

    /** The client (tab to tab) communication channel. */
    #commChannel: ClientCommChannel = null;

    /** The sidebar element. */
    $mainSidebar: JQuery = null;

    /** The page container element. */
    $pageContainer: JQuery = null;

    /** The page content element. */
    $pageContent: JQuery = null;

    /** The window, wrapped in JQuery. */
    $window: JQuery<Window>;

    /** The currently-shown pane for the sidebar. */
    _$mainSidebarPane: JQuery = null;

    /** The page sidebar element */
    _$pageSidebar: JQuery = null;

    /** The set of all panes in the sidebar. */
    _$pageSidebarPanes: JQuery = null;

    /** A list of all registered action views. */
    _actionViews: ActionView[] = [];

    /** The pop-out drawer, if the page has one. */
    drawer: RB.Drawer = null;

    /** Whether the page has a sidebar. */
    hasSidebar: boolean = null;

    /** The view for the page header. */
    headerView: RB.HeaderView = null;

    /** Whether the page is currently in a mobile view. */
    inMobileMode: boolean = null;

    /** Whether the page is rendered in full-page content mode. */
    isFullPage: boolean = null;

    /**
     * Whether the page is rendered.
     *
     * Deprecated:
     *     6.0:
     *     Users should use :js:attr:`rendered` instead.
     */
    isPageRendered = false;

    options: PageViewOptions;

    /**
     * Initialize the page.
     *
     * Args:
     *     options (PageViewOptions, optional):
     *         Options for the page.
     */
    initialize(options: PageViewOptions = {}) {
        this.options = options;
        this.$window = $(window);

        if (!window.rbRunningTests) {
            this.#commChannel = new ClientCommChannel();
            this.listenTo(this.#commChannel, 'reload', () => {
                alert(_`This page is out of date and needs to be reloaded.`);
                RB.reload();
            });
        }
    }

    /**
     * Remove the page from the DOM and disable event handling.
     *
     * Returns:
     *     PageView:
     *     This object, for chaining.
     */
    remove(): this {
        if (this.$window) {
            this.$window.off('resize.rbPageView');
        }

        if (this.headerView) {
            this.headerView.remove();
        }

        return super.remove();
    }

    /**
     * Render the page.
     *
     * Subclasses should not override this. Instead, they should override
     * :js:func:`RB.PageView.renderPage``.
     */
    onInitialRender() {
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
            $body: $body,
            $pageSidebar: this._$pageSidebar,
            el: options.$headerBar || $('#headerbar'),
        });
        this.headerView.render();

        this.hasSidebar = $body.hasClass('-has-sidebar') ||
                          $body.hasClass('has-sidebar');
        this.isFullPage = $body.hasClass('-is-content-full-page') ||
                          $body.hasClass('full-page-content');
        this.inMobileMode = this.headerView.inMobileMode;

        this.renderPage();

        /*
         * Now that we've rendered the elements, we can show the page.
         */
        $body.addClass('-is-loaded');

        this.$window.on('resize.rbPageView',
                        _.throttle(() => this._updateSize(),
                                   this.windowResizeThrottleMS));
        this.listenTo(this.headerView, 'mobileModeChanged',
                      this._onMobileModeChanged);
        this._onMobileModeChanged(this.inMobileMode);

        this._actionViews.forEach(actionView => actionView.render());

        this.isPageRendered = true;
    }

    /**
     * Return data to use for assessing cross-tab page reloads.
     *
     * This is intended to be overridden by subclasses in order to filter which
     * reload signals apply to this page.
     *
     * Version Added:
     *     6.0
     */
    getReloadData(): unknown {
        return null;
    }

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
    setDrawer(drawer: RB.Drawer) {
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
    }

    /**
     * Render the page contents.
     *
     * This should be implemented by subclasses that need to render any
     * UI elements.
     */
    renderPage() {
        // Do nothing.
    }

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
    resizeElementForFullHeight(
        $el: JQuery,
        $parent?: JQuery,
    ) {
        if ($parent === undefined) {
            $parent = this.$pageContainer;
        }

        $el.outerHeight($parent.height() - $el.position().top);
    }

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
        // Do nothing.
    }

    /**
     * Handle mobile mode changes.
     *
     * This will be called whenever the page goes between mobile/desktop
     * mode, allowing subclasses to adjust any UI elements as appropriate.
     *
     * Args:
     *     inMobileMode (boolean):
     *         Whether the UI is now in mobile mode. This will be the same
     *         value as :js:attr:`inMobileMode`, and is just provided for
     *         convenience.
     */
    onMobileModeChanged(inMobileMode: boolean) {
        // Do nothing.
    }

    /**
     * Add an action to the page.
     *
     * Args:
     *     actionView (RB.ActionView):
     *         The action instance.
     */
    addActionView(actionView: ActionView) {
        this._actionViews.push(actionView);

        if (this.isPageRendered) {
            actionView.render();
        }
    }

    /**
     * Return the action view for the given action ID.
     *
     * Args:
     *     actionId (string):
     *         The ID of the action.
     *
     * Returns:
     *     RB.ActionView:
     *     The view for the given action.
     */
    getActionView(
        actionId: string,
    ): ActionView {
        for (const view of this._actionViews) {
            if (view.model.get('actionId') === actionId) {
                return view;
            }
        }

        return null;
    }

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
    protected _updateSize() {
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
    }

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
    protected _reparentDrawer() {
        const $el = this.drawer.$el
            .detach();

        if (this.inMobileMode) {
            $el.insertBefore(this._$pageSidebar);
        } else {
            $el.appendTo(this._$pageSidebarPanes);
        }
    }

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
    protected _onMobileModeChanged(inMobileMode: boolean) {
        this.inMobileMode = inMobileMode;

        this._updateSize();

        if (this.drawer !== null) {
            this._reparentDrawer();
        }

        this.onMobileModeChanged(this.inMobileMode);
        this.trigger('inMobileModeChanged', this.inMobileMode);
    }
}
