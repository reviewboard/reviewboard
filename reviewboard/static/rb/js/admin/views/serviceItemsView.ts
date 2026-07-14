/**
 * View for a hosting service's expandable items list.
 *
 * Version Added:
 *     9.0
 */

import {
    type PaginatorView,
    craft,
    paint,
} from '@beanbag/ink';
import {
    BaseView,
    spina,
} from '@beanbag/spina';
import _ from 'underscore';


/**
 * An account offered in the items filter dropdown.
 *
 * Version Added:
 *     9.0
 */
interface FilterAccount {
    /** The account's primary key. */
    id: number | string;

    /** The account's display label. */
    label: string;
}


/**
 * The display strings for a service items list.
 *
 * These localize the list for the kind of item being shown (repositories,
 * bug trackers, etc.).
 *
 * Version Added:
 *     9.0
 */
export interface ServiceItemsViewStrings {
    /** The label for the search field. */
    filterLabel: string;

    /** The placeholder for the search field. */
    filterPlaceholder: string;

    /** The error message shown when the list cannot be loaded. */
    loadError: string;

    /** The message shown while the list is loading. */
    loading: string;

    /** The ARIA label for the paginator. */
    paginatorLabel: string;
}


/**
 * Options for ServiceItemsView.
 *
 * Version Added:
 *     9.0
 */
export interface ServiceItemsViewOptions {
    /**
     * A URL template for the endpoint returning the items fragment.
     *
     * This contains the placeholder ``__SERVICE_ID__``, which is replaced
     * with the ID of the service this list belongs to.
     */
    itemsURLTemplate: string;

    /**
     * The number of items the endpoint returns per page.
     *
     * This must match the page size the endpoint paginates by. It's provided
     * by the server rather than hard-coded, so the two can't drift.
     */
    perPage: number;

    /** The display strings for the kind of item being shown. */
    strings: ServiceItemsViewStrings;
}


/**
 * View for a hosting service's expandable items list.
 *
 * This backs one ``.rb-c-admin-cs-service-items`` block on the Connected
 * Services admin page. Clicking the disclosure header expands a panel
 * listing the service's items (repositories or bug tracker configurations),
 * fetched from an admin endpoint as an HTML fragment.
 *
 * When the service has no more items than fit on a page, the panel just shows
 * the list. When there are more, it also builds a search box, an account
 * filter (when there are multiple connected accounts), and a paginator. Those
 * controls persist across fetches; only the list itself is swapped.
 *
 * Version Added:
 *     9.0
 */
@spina
export class ServiceItemsView extends BaseView<
    undefined,
    HTMLElement,
    ServiceItemsViewOptions
> {
    /**********************
     * Instance variables *
     **********************/

    /** The currently-selected account ID, or an empty string for all. */
    #account = '';

    /** The accounts available for filtering. */
    #accounts: FilterAccount[] = [];

    /** The account filter dropdown, when built. */
    #accountSelectEl: (HTMLSelectElement | null) = null;

    /** The current page number (1-based). */
    #currentPage = 1;

    /** The debounced search handler. */
    #debouncedSearch: () => void;

    /** Whether the panel is currently expanded. */
    #expanded = false;

    /** The disclosure button that expands and collapses the panel. */
    #headerEl: (HTMLButtonElement | null) = null;

    /** The items endpoint URL, resolved for this service. */
    #itemsURL: string;

    /** The URL template for the items endpoint. */
    #itemsURLTemplate: string;

    /** Whether the panel has been built and loaded once. */
    #loaded = false;

    /** The total number of pages, from the last fetch. */
    #numPages = 1;

    /** The Ink paginator, when built. */
    #paginator: (PaginatorView | null) = null;

    /** The paginator's container element, when built. */
    #paginatorEl: (HTMLElement | null) = null;

    /** The panel element that holds the expanded content. */
    #panelEl: HTMLElement;

    /** The number of items the endpoint returns per page. */
    #perPage: number;

    /** The container the fetched list fragment is rendered into. */
    #resultsEl: (HTMLElement | null) = null;

    /** A monotonic token used to drop stale fetch responses. */
    #requestSeq = 0;

    /** The current search term. */
    #search = '';

    /** The search input, when built. */
    #searchInputEl: (HTMLInputElement | null) = null;

    /** The hosting service ID to fetch items for. */
    #serviceId: string;

    /** The display strings for the kind of item being shown. */
    #strings: ServiceItemsViewStrings;

    /** The total number of items, as rendered by the server. */
    #totalCount: number;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (ServiceItemsViewOptions):
     *         The options for the view.
     */
    initialize(options: ServiceItemsViewOptions) {
        this.#itemsURLTemplate = options.itemsURLTemplate;
        this.#perPage = options.perPage;
        this.#strings = options.strings;
    }

    /**
     * Render the view.
     */
    protected onInitialRender() {
        const el = this.el;

        this.#serviceId = el.dataset.serviceId ?? '';
        this.#itemsURL = this.#itemsURLTemplate.replace(
            '__SERVICE_ID__', encodeURIComponent(this.#serviceId));
        this.#totalCount =
            parseInt(el.dataset.itemCount ?? '0', 10) || 0;
        this.#panelEl = el.querySelector<HTMLElement>(
            '.rb-c-admin-cs-service-items__panel');

        const accountsEl = el.querySelector(
            '.rb-c-admin-cs-service-items__accounts');

        if (accountsEl) {
            try {
                this.#accounts =
                    JSON.parse(accountsEl.textContent ?? '[]') ?? [];
            } catch (err) {
                console.error('Could not parse the connected accounts for ' +
                              'service "%s": %s',
                              this.#serviceId, err);
                this.#accounts = [];
            }
        }

        this.#debouncedSearch = _.debounce(() => this.#onSearchInput(), 300);

        this.#headerEl = el.querySelector<HTMLButtonElement>(
            '.rb-c-admin-cs-service-items__header');

        if (this.#headerEl) {
            this.#headerEl.addEventListener('click', () => this.#toggle());
        }
    }

    /**
     * Toggle the panel open or closed.
     *
     * The content is loaded the first time the panel is opened. Later toggles
     * just show or hide the already-loaded panel.
     */
    #toggle() {
        const expanded = !this.#expanded;
        this.#expanded = expanded;

        const disclosure = this.el.querySelector(
            '.rb-c-admin-cs-service-items__disclosure');

        if (disclosure) {
            disclosure.classList.toggle('-is-open', expanded);
        }

        this.#headerEl?.setAttribute('aria-expanded', String(expanded));

        this.#panelEl.hidden = !expanded;

        if (expanded && !this.#loaded) {
            this.#load();
        }
    }

    /**
     * Build the panel and load the first page.
     */
    #load() {
        this.#loaded = true;

        const paginated = (this.#totalCount > this.#perPage);

        if (paginated) {
            this.#buildFilterUI();
        }

        this.#resultsEl = paint<HTMLDivElement>`
            <div class="rb-c-admin-cs-service-items__results-container"/>
        `;
        this.#panelEl.appendChild(this.#resultsEl);

        if (paginated) {
            this.#buildPaginator();
        }

        this.#fetchPage(1);
    }

    /**
     * Build the filter row (search box and optional account dropdown).
     */
    #buildFilterUI() {
        const strings = this.#strings;

        const searchInputEl = paint<HTMLInputElement>`
            <input class="rb-c-search-field__input"
                   type="search"
                   aria-label="${strings.filterLabel}"
                   placeholder="${strings.filterPlaceholder}"/>
        `;
        searchInputEl.addEventListener('input', () => this.#debouncedSearch());
        this.#searchInputEl = searchInputEl;

        const filterEl = paint<HTMLDivElement>`
            <div class="rb-c-admin-cs-service-items__filter">
             <div class="rb-c-search-field">
              <span class="ink-i-search" aria-hidden="true"></span>
              ${searchInputEl}
             </div>
            </div>
        `;

        if (this.#accounts.length >= 2) {
            const selectEl = paint<HTMLSelectElement>`
                <select class="rb-c-admin-cs-service-items__filter__account"
                        aria-label="${gettext('Filter by account')}">
                 <option value="">${gettext('All accounts')}</option>
                 ${this.#accounts.map(account => paint`
                  <option value="${String(account.id)}">
                   ${account.label}
                  </option>
                 `)}
                </select>
            `;
            selectEl.addEventListener('change', () => this.#onAccountChange());
            this.#accountSelectEl = selectEl;
            filterEl.appendChild(selectEl);
        }

        this.#panelEl.appendChild(filterEl);
    }

    /**
     * Build the persistent paginator.
     */
    #buildPaginator() {
        this.#paginatorEl = paint<HTMLDivElement>`
            <div class="rb-c-admin-cs-service-items__paginator" hidden/>
        `;
        this.#panelEl.appendChild(this.#paginatorEl);

        this.#paginator = craft<PaginatorView>`
            <Ink.Paginator
              ariaLabel="${this.#strings.paginatorLabel}"
              onPageSelect=${(page: number) => this.#fetchPage(page)}/>
        `;
        this.#paginator.renderInto(this.#paginatorEl);
    }

    /**
     * Handle a change to the search field.
     */
    #onSearchInput() {
        const value = this.#searchInputEl?.value.trim() ?? '';

        if (value === this.#search) {
            return;
        }

        this.#search = value;
        this.#fetchPage(1);
    }

    /**
     * Handle a change to the account filter.
     */
    #onAccountChange() {
        this.#account = this.#accountSelectEl?.value ?? '';
        this.#fetchPage(1);
    }

    /**
     * Fetch and render a page of items.
     *
     * Args:
     *     page (number):
     *         The 1-based page number to fetch.
     */
    async #fetchPage(page: number) {
        const resultsEl = this.#resultsEl;

        if (!resultsEl) {
            return;
        }

        /*
         * We store a monotonic token so that while the user is doing typeahead
         * search, any stale page fetches that return late don't overwrite
         * later responses.
         *
         * Because `fetch` and `response.text()` are both async, we have to check
         * this value against this.#requestSeq explicitly at every point
         * instead of precomputing the stale state.
         */
        const seq = ++this.#requestSeq;

        if (!resultsEl.hasChildNodes()) {
            resultsEl.innerHTML =
                `<p class="rb-c-admin-cs-service-items__results__loading">${
                    this.#strings.loading}</p>`;
        }

        resultsEl.setAttribute('aria-busy', 'true');

        try {
            const response = await fetch(this.#buildURL(page));

            if (seq !== this.#requestSeq) {
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            /*
             * An expired session redirects to the admin login page, which
             * fetch follows transparently and reports as a successful HTML
             * response. Rendering that would drop a login form into the
             * list, so treat any redirect as a failure.
             */
            if (response.redirected) {
                throw new Error(`Redirected to ${response.url}`);
            }

            const numPages = parseInt(
                response.headers.get('X-Num-Pages') ?? '1', 10);
            const pageNumber = parseInt(
                response.headers.get('X-Page-Number') ?? '1', 10);
            const html = await response.text();

            if (seq !== this.#requestSeq) {
                return;
            }

            this.#currentPage = pageNumber || 1;
            this.#numPages = numPages || 1;
            resultsEl.innerHTML = html;
            resultsEl.classList.toggle('-is-paginated', this.#numPages > 1);
            this.#updatePaginator();
        } catch (err) {
            console.error('Could not load page %s of the "%s" list for ' +
                          'service "%s": %s',
                          page, this.el.dataset.itemType, this.#serviceId,
                          err);

            if (seq === this.#requestSeq) {
                this.#renderError();
            }
        } finally {
            if (seq === this.#requestSeq) {
                resultsEl.removeAttribute('aria-busy');
            }
        }
    }

    /**
     * Build the fetch URL for a page.
     *
     * Args:
     *     page (number):
     *         The 1-based page number to request.
     *
     * Returns:
     *     string:
     *     The URL to fetch.
     */
    #buildURL(
        page: number,
    ): string {
        const params = new URLSearchParams();

        if (this.#account) {
            params.set('account', this.#account);
        }

        if (this.#search) {
            params.set('q', this.#search);
        }

        params.set('page', String(page));

        return `${this.#itemsURL}?${params.toString()}`;
    }

    /**
     * Update the paginator controls from the last fetch.
     */
    #updatePaginator() {
        const paginatorEl = this.#paginatorEl;
        const paginator = this.#paginator;

        if (!paginatorEl || !paginator) {
            return;
        }

        paginatorEl.hidden = (this.#numPages <= 1);
        paginator.pages = this.#numPages;
        paginator.page = this.#currentPage;
    }

    /**
     * Render an error state with a retry control.
     */
    #renderError() {
        const resultsEl = this.#resultsEl;

        if (!resultsEl) {
            return;
        }

        const retryEl = paint<HTMLButtonElement>`
            <button type="button" class="ink-c-button">
             ${gettext('Retry')}
            </button>
        `;
        retryEl.addEventListener(
            'click', () => this.#fetchPage(this.#currentPage));

        resultsEl.replaceChildren(
            paint<HTMLParagraphElement>`
                <p class="rb-c-admin-cs-service-items__results__error">
                 ${this.#strings.loadError}
                </p>
            `,
            retryEl);

        if (this.#paginatorEl) {
            this.#paginatorEl.hidden = true;
        }
    }
}
