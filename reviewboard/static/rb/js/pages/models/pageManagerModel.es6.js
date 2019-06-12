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
        this.set('rendered', true);
    },
}, {
    instance: null,

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
     *     page (RB.Page):
     *         The page to set.
     */
    setPage(page) {
        this.instance.set('page', page);
    },

    /**
     * Return the page set on the PageManager instance.
     *
     * Returns:
     *     RB.Page:
     *     The current page instance.
     */
    getPage() {
        return this.instance.get('page');
    },
});


RB.PageManager.instance = new RB.PageManager();
