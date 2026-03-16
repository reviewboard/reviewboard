/**
 * Site Header
 */

import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';


/**
 * Options for the HeaderView.
 *
 * Version Added:
 *     8.0
 */
interface HeaderViewOptions {
    /**
     * The body element to use.
     *
     * This is used when running unit tests.
     */
    $body?: JQuery;

    /**
     * The page sidebar to use.
     *
     * This is used when running unit tests.
     */
    $pageSidebar?: JQuery;
}


/**
 * Site Header
 */
@spina
export class HeaderView extends BaseView<
    undefined, HTMLElement, HeaderViewOptions
> {
    static SEARCH_SUMMARY_TRIM_LEN = 28;
    static DESKTOP_SEARCH_RESULTS_WIDTH = 350;

    static events: EventsHash = {
        'click #nav_toggle': '_handleNavClick',
        'focus #search_field': '_closeMobileMenu',
        'touchstart #nav_toggle': '_handleNavClick',
    };

    /** The instance of the HeaderView. */
    static instance: HeaderView = null;

    /**
     * Ensure that this HeaderView is the only one on the page.
     *
     * This exists in a separate function so that unit tests can disable this
     * check.
     */
    _ensureSingleton() {
        if (HeaderView.instance !== null) {
            console.warn('There are two instances of RB.HeaderView on the ' +
                         'page. Make sure only one RB.PageView is ' +
                         'instantiated and registered through ' +
                         'RB.PageManager.setupPage().');
        } else {
            HeaderView.instance = this;
        }
    }

    /**********************
     * Instance variables *
     **********************/

    /** Whether the page is currently in mobile mode. */
    inMobileMode: boolean = undefined;

    /** Saved options for the view. */
    options: HeaderViewOptions;

    /** The saved window instance. */
    #$window: JQuery<Window> = null;

    /** The main body element. */
    #$body: JQuery = null;

    /** The mobile menu toggle button. */
    #$navToggle: JQuery = null;

    /** The mask overlay for the mobile menu. */
    #$mobileMenuMask: JQuery = null;

    /** Whether the mobile menu is open. */
    #mobileMenuOpened = false;

    /** The function to recalculate whether the page is in mobile mode. */
    #recalcFunc: () => void;

    /**
     * Initialize the header.
     *
     * Args:
     *     options (HeaderViewOptions, optional):
     *         Options for the view.
     */
    initialize(options: HeaderViewOptions = {}) {
        this._ensureSingleton();

        this.#$window = $(window);
        this.#$body = options.$body || $(document.body);
        this.options = options;
    }

    /**
     * Remove the view from the DOM and disable event handling.
     *
     * This will also unset :js:attr:`RB.HeaderView.instance`, if currently
     * set to this instance.
     */
    onRemove() {
        if (this.$el.attr('id')) {
            console.trace();
        }

        if (HeaderView.instance === this) {
            HeaderView.instance = null;
        }

        if (this.#$window) {
            this.#$window.off('resize.rbHeaderView', this.#recalcFunc);
        }
    }

    /**
     * Render the header.
     */
    onInitialRender() {
        this.#$navToggle = $('#nav_toggle');
        this.#$mobileMenuMask = $('<div id="mobile_menu_mask">')
            .on('click touchstart', this._closeMobileMenu.bind(this))
            .insertAfter(this.options.$pageSidebar || $('#page-sidebar'));

        this.#recalcFunc = _.throttle(this.#recalcMobileMode.bind(this), 100);

        this.#$window.on('resize.rbHeaderView', this.#recalcFunc);
        this.#recalcMobileMode();

        this.#setupSearch();
    }

    /**
     * Handle a click on the mobile navigation menu.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    _handleNavClick(e: Event) {
        e.stopPropagation();
        e.preventDefault();

        this.#setMobileMenuOpened(!this.#mobileMenuOpened);
    }

    /**
     * Recalculate whether the header and nav menu is in mobile mode.
     */
    #recalcMobileMode() {
        const inMobileMode = this.#$navToggle.is(':visible');

        if (inMobileMode === this.inMobileMode) {
            return;
        }

        if (!inMobileMode) {
            this.#setMobileMenuOpened(false);
        }

        this.inMobileMode = inMobileMode;
        this.trigger('mobileModeChanged', inMobileMode);
    }

    /**
     * Close the mobile menu.
     *
     * This is used as an event handler, to make it easy to close the
     * mobile menu and prevent any bubbling or default actions from the
     * event.
     */
    _closeMobileMenu() {
        this.#setMobileMenuOpened(false);

        return false;
    }

    /**
     * Set up the search auto-complete field.
     */
    #setupSearch() {
        $('#search_field').rbautocomplete({
            clickToURL: true,
            enterToURL: true,
            extraParams: {
                'only-fields': 'display_name,fullname,id,name,' +
                               'public,summary,url,username',
                'only-links': '',
            },
            formatItem: data => {
                let s;

                if (data.username) {
                    // For the format of users:
                    s = data.username;

                    if (data.fullname) {
                        s += ` <span>(${_.escape(data.fullname)})</span>`;
                    }

                } else if (data.name) {
                    // For the format of groups:
                    const displayName = _.escape(data.display_name);
                    s = `${data.name} <span>(${displayName})</span>`;
                } else if (data.summary) {
                    // For the format of review requests:
                    if (data.summary.length <
                        HeaderView.SEARCH_SUMMARY_TRIM_LEN) {
                        s = data.summary;
                    } else {
                        s = data.summary.substring(
                            0, HeaderView.SEARCH_SUMMARY_TRIM_LEN);
                    }

                    s += ` <span>(${_.escape(data.id)})</span>`;
                }

                return s;
            },
            matchCase: false,
            multiple: false,
            parse: data => {
                const objects = ['users', 'groups', 'review_requests'];
                const keys = ['username', 'name', 'summary'];

                const parsed = [];

                for (let j = 0; j < objects.length; j++) {
                    const object = objects[j];
                    const items = data.search[object];

                    for (let i = 0; i < items.length; i++) {
                        const value = items[i];
                        const key = keys[j];


                        if (j !== 2) {
                            // For users and groups, always show.
                            parsed.push({
                                data: value,
                                result: value[key],
                                value: value[key],
                            });
                        } else if (value.public) {
                            /*
                             * For review requests, only show ones that are
                             * public.
                             */
                            parsed.push({
                                data: value,
                                result: value[key],
                                value: value[key],
                            });
                        }
                    }
                }

                return parsed;
            },
            resultsClass: 'ui-autocomplete-results search-results',
            resultsParentEl: $('#page-container'),
            selectFirst: false,
            url: `${SITE_ROOT}api/search/`,
            width: HeaderView.DESKTOP_SEARCH_RESULTS_WIDTH,
        });
    }

    /**
     * Set whether the mobile menu is opened.
     *
     * Args:
     *     opened (boolean):
     *         Whether the menu is open.
     */
    #setMobileMenuOpened(opened: boolean) {
        if (opened === this.#mobileMenuOpened) {
            return;
        }

        if (opened) {
            this.#$mobileMenuMask.show();
            _.defer(() => this.#$body.addClass('js-mobile-menu-open'));
        } else {
            this.#$body.removeClass('js-mobile-menu-open');
            _.delay(() => this.#$mobileMenuMask.hide(), 300);
        }

        this.#mobileMenuOpened = opened;
    }
}
