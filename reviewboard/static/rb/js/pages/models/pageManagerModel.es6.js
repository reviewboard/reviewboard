/**
 * Manages the current page.
 *
 * Callers can set or get the current page by getting/setting the
 * currentPage attribute.
 *
 * Callers can also delay any operations until there's a valid page with
 * a ready DOM by wrapping their logic in a call to PageManager.ready().
 */
RB.PageManager = Backbone.Model.extend({
    defaults: {
        page: null,
        rendered: false,
    },

    /**
     * Initialize the PageManager.
     *
     * This will listen for when a page is set, and will handle rendering
     * the page, once the DOM is ready. Listeners will be notified before
     * and after render.
     */
    initialize() {
        this.once('change:page', () => {
            this.trigger('beforeRender');

            if (document.readyState === 'complete') {
                /*
                 * $(cb) will also call immediately if the DOM is already
                 * loaded, but it does so asynchronously, which interferes with
                 * some unit tests.
                 */
                this._renderPage();
            } else {
                $(this._renderPage.bind(this));
            }
        });
    },

    /**
     * Add a callback to be called before rendering the page.
     *
     * If the page has been set, but isn't yet rendered, this will call
     * the callback immediately.
     *
     * If the page is not set, the callback will be called once set and
     * before rendering.
     *
     * If the page is set and rendered, this will assert.
     *
     * Args:
     *     cb (function):
     *         The callback to be called before the page is rendered.
     *
     *     context (object):
     *         The context to use when calling the callback.
     */
    beforeRender(cb, context) {
        console.assert(!this.get('rendered'),
                       'beforeRender called after page was rendered');

        const page = this.get('page');

        if (page) {
            cb.call(context, page);
        } else {
            this.once('beforeRender', () => cb.call(context, this.get('page')));
        }
    },

    /**
     * Add a callback to be called after the page is rendered and ready.
     *
     * If the page has been set and is rendered, this will call the callback
     * immediately.
     *
     * If the page is not set or not yet rendered, the callback will be
     * called once set and rendered.
     *
     * Args:
     *     cb (function):
     *         The callback to be called after the page is ready.
     *
     *     context (object):
     *         The context to use when calling the callback.
     */
    ready(cb, context) {
        const page = this.get('page');

        if (page && this.get('rendered')) {
            cb.call(context, page);
        } else {
            this.once('change:rendered', () => cb.call(context, this.get('page')));
        }
    },

    /**
     * Renders the page and sets the rendered state.
     */
    _renderPage() {
        this.get('page').render();

        const headerView = RB.HeaderView.instance;

        if (!headerView.isRendered) {
            /*
             * The RB.PageView subclass did not render the page. It probably
             * provided its own render() that didn't call the parent. REnder
             * it here.
             *
             * This is deprecated and can be removed in Review Board 5.0.
             */
            headerView.render();
        }

        this.set('rendered', true);
    },
}, {
    instance: null,

    /**
     * Set up the current page view and model.
     *
     * Args:
     *     options (object):
     *         The options for setting up the page.
     *
     * Option Args:
     *     modelType (prototype, optional):
     *         The :js:class:`RB.Page` model class or subclass for the page.
     *
     *     modelAttrs (object, optional):
     *         The attribute used to construct the ``modelType``.
     *
     *     viewType (prototype, optional):
     *         The :js:class:`RB.PageView` view class or subclass for the page.
     *
     *     viewOptions (object, optional):
     *         The options used to construct the ``viewType``.
     */
    setupPage(options) {
        /*
         * Only set up the page if we haven't already set one up. Ideally,
         * we'd assert here, but we need to support older templates that
         * manually instantiate a PageView subclass. Instead, we're going to
         * leave the assertion to the PageView constructor.
         */
        const curPage = this.getPage();

        if (curPage !== null) {
            console.warn([
                'A subclass of RB.PageView has already been set up in the ',
                'PageManager. This might be an older template manually ',
                'instantiating a PageView.\n',
                '\n',
                'Please update your template to use the js-page-view-type, ',
                'js-page-view-options, js-page-model-type, ',
                'js-page-model-type, and js-page-model-options blocks.\n',
                '\n',
                'Make sure they also call the parent initialize() method and ',
                'override renderPage() instead of render().\n',
                '\n',
                'Support for legacy page registration is deprecated and will ',
                'be removed in Review Board 5.0.',
            ].join(''));

            /*
             * Legacy pages may or may not have called the parent initialize()
             * and render(). If they haven't, we need to manage it here, for
             * backwards-compatibility.
             */
            if (RB.HeaderView.instance === null) {
                new RB.HeaderView({
                    el: $('#headerbar'),
                });
            }
        } else {
            const pageView = new options.viewType(_.extend({
                el: document.body,
                model: new options.modelType(options.modelAttrs,
                                             options.modelOptions),
            }, options.viewOptions));

            this.setPage(pageView);
        }
    },

    /**
     * Call beforeRender on the PageManager instance.
     *
     * Args:
     *     cb (function):
     *         The callback to be called before the page is rendered.
     *
     *     context (object):
     *         The context to use when calling the callback.
     */
    beforeRender(cb, context) {
        this.instance.beforeRender(cb, context);
    },

    /**
     * Call ready on the PageManager instance.
     *
     * Args:
     *     cb (function):
     *         The callback to be called after the page is ready.
     *
     *     context (object):
     *         The context to use when calling the callback.
     */
    ready(cb, context) {
        this.instance.ready(cb, context);
    },

    /**
     * Set the page on the PageManager instance.
     *
     * Args:
     *     page (RB.PageView):
     *         The page view to set.
     */
    setPage(page) {
        this.instance.set('page', page);
    },

    /**
     * Return the page set on the PageManager instance.
     *
     * Returns:
     *     RB.PageView:
     *     The current page view instance.
     */
    getPage() {
        return this.instance.get('page');
    },
});


RB.PageManager.instance = new RB.PageManager();
