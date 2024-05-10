/**
 * Manages the current page.
 */

import {
    type ModelAttributes,
    type Result,
    BaseModel,
    spina,
} from '@beanbag/spina';

import {
    type PageView,
    type PageViewOptions,
} from '../views/pageView';
import { type Page } from './pageModel';


/**
 * Attributes for the PageManager model.
 *
 * Version Added:
 *     8.0
 */
interface PageManagerAttrs extends ModelAttributes {
    /** The page instance. */
    page: PageView | null;

    /** Whether the page has been rendered. */
    rendered: boolean;
}


/**
 * Declaration for a class type of a Page model subclass.
 *
 * Version Added:
 *     8.0
 */
interface PageModelClass<
    TPage extends Page,
    TPageAttributes extends ModelAttributes,
    TPageOptions,
> {
    new(
        attributes?: Backbone._NoInfer<Partial<TPageAttributes>>,
        options?: Backbone.CombinedModelConstructorOptions<
            Backbone._NoInfer<TPageOptions>>
    ): TPage;
}


/**
 * Declaration for a class type of a PageView subclass.
 *
 * Version Added:
 *     8.0
 */
interface PageViewClass<
    TPage extends Page,
    TPageView extends PageView,
    TPageViewOptions extends PageViewOptions,
> {
    new(
        options?: Backbone.CombinedViewConstructorOptions<
            Backbone._NoInfer<TPageViewOptions>,
            TPage,
            HTMLBodyElement>,
    ): TPageView;
}


/**
 * Options for the PageManager.setupPage operation.
 *
 * Version Added:
 *     8.0
 */
interface SetupPageOptions<
    TPage extends Page = Page,
    TPageAttributes extends ModelAttributes = ModelAttributes,
    TPageOptions = unknown,
    TPageView extends PageView = PageView,
    TPageViewOptions extends PageViewOptions = PageViewOptions,
> {
    /** The page model to instantiate. */
    modelType: PageModelClass<TPage, TPageAttributes, TPageOptions>;

    /** Attributes to pass to the page model. */
    modelAttrs: TPageAttributes;

    /** Options to pass to the page model. */
    modelOptions: TPageOptions;

    /** The page view to instantiate. */
    viewType: PageViewClass<TPage, TPageView, TPageViewOptions>;

    /** Options to pass to the page view. */
    viewOptions: TPageViewOptions;
}


/**
 * Manages the current page.
 *
 * Callers can set or get the current page by getting/setting the
 * currentPage attribute.
 *
 * Callers can also delay any operations until there's a valid page with
 * a ready DOM by wrapping their logic in a call to PageManager.ready().
 */
@spina
export class PageManager extends BaseModel<PageManagerAttrs> {
    static defaults: Result<Partial<PageManagerAttrs>> = {
        page: null,
        rendered: false,
    };

    /** The PageManager global instance. */
    static instance: PageManager = null;

    /**
     * Set up the current page view and model.
     *
     * Args:
     *     options (object):
     *         The options for setting up the page.
     */
    static setupPage<
        TPage extends Page = Page,
        TPageAttributes extends ModelAttributes = ModelAttributes,
        TPageOptions = unknown,
        TPageView extends PageView = PageView,
        TPageViewOptions extends PageViewOptions = PageViewOptions,
    >(
        options: SetupPageOptions<
            TPage, TPageAttributes, TPageOptions, TPageView, TPageViewOptions
        >,
    ) {
        console.assert(this.getPage() === null);

        const pageView = new options.viewType(Object.assign({
            el: document.body as HTMLBodyElement,
            model: new options.modelType(options.modelAttrs,
                                         options.modelOptions),
        }, options.viewOptions));

        this.setPage(pageView);
    }

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
    static beforeRender(
        cb: (page: PageView) => void,
        context?: unknown,
    ) {
        this.instance.beforeRender(cb, context);
    }

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
    static ready(
        cb: (page: PageView) => void,
        context?: unknown,
    ) {
        this.instance.ready(cb, context);
    }

    /**
     * Set the page on the PageManager instance.
     *
     * Args:
     *     page (RB.PageView):
     *         The page view to set.
     */
    static setPage(page: PageView) {
        this.instance.set('page', page);
    }

    /**
     * Return the page set on the PageManager instance.
     *
     * Returns:
     *     RB.PageView:
     *     The current page view instance.
     */
    static getPage(): PageView | null {
        return this.instance.get('page');
    }

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
    }

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
    beforeRender(
        cb: (page: PageView) => void,
        context?: unknown,
    ) {
        console.assert(!this.get('rendered'),
                       'beforeRender called after page was rendered');

        const page = this.get('page');

        if (page) {
            cb.call(context, page);
        } else {
            this.once('beforeRender',
                      () => cb.call(context, this.get('page')));
        }
    }

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
    ready(
        cb: (page: PageView) => void,
        context?: unknown,
    ) {
        const page = this.get('page');

        if (page && this.get('rendered')) {
            cb.call(context, page);
        } else {
            this.once('change:rendered',
                      () => cb.call(context, this.get('page')));
        }
    }

    /**
     * Renders the page and sets the rendered state.
     *
     * This is public for consumption in unit tests.
     */
    _renderPage() {
        this.get('page').render();
        this.set('rendered', true);
    }
}


PageManager.instance = new PageManager();
