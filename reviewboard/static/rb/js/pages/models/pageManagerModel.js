/*
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
        rendered: false
    },

    /*
     * Initializes the PageManager.
     *
     * This will listen for when a page is set, and will handle rendering
     * the page, once the DOM is ready. Listeners will be notified before
     * and after render.
     */
    initialize: function() {
        this.once('change:page', function() {
            this.trigger('beforeRender');

            $(document).ready(_.bind(this._renderPage, this));
        }, this);
    },

    /*
     * Adds a callback to be called before rendering the page.
     *
     * If the page has been set, but isn't yet rendered, this will call
     * the callback immediately.
     *
     * If the page is not set, the callback will be called once set and
     * before rendering.
     *
     * If the page is set and rendered, this will assert.
     */
    beforeRender: function(cb, context) {
        var page = this.get('page');

        console.assert(!this.get('rendered'),
                       'beforeRender called after page was rendered');

        if (page) {
            cb.call(context, page);
        } else {
            this.once('beforeRender', function() {
                cb.call(context, this.get('page'));
            }, this);
        }
    },

    /*
     * Adds a callback to be called after the page is rendered and ready.
     *
     * If the page has been set and is rendered, this will call the callback
     * immediately.
     *
     * If the page is not set or not yet rendered, the callback will be
     * called once set and rendered.
     */
    ready: function(cb, context) {
        var page = this.get('page');

        if (page && this.get('rendered')) {
            cb.call(context, page);
        } else {
            this.once('change:rendered', function() {
                cb.call(context, this.get('page'));
            }, this);
        }
    },

    /*
     * Renders the page and sets the rendered state.
     */
    _renderPage: function() {
        this.get('page').render();
        this.set('rendered', true);
    }
}, {
    instance: null,

    /*
     * Calls beforeRender on the PageManager instance.
     */
    beforeRender: function(cb, context) {
        this.instance.beforeRender(cb, context);
    },

    /*
     * Calls ready on the PageManager instance.
     */
    ready: function(cb, context) {
        this.instance.ready(cb, context);
    },

    /*
     * Sets the page on the PageManager instance.
     */
    setPage: function(page) {
        this.instance.set('page', page);
    },

    /*
     * Returns the page set on the PageManager instance.
     */
    getPage: function() {
        return this.instance.get('page');
    }
});

RB.PageManager.instance = new RB.PageManager();
