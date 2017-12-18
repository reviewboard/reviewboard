/**
 * Site Header
 */
RB.HeaderView = Backbone.View.extend({
    SEARCH_SUMMARY_TRIM_LEN: 28,
    DESKTOP_SEARCH_RESULTS_WIDTH: 350,

    events: {
        'click #nav_toggle': '_handleNavClick',
        'touchstart #nav_toggle': '_handleNavClick',
        'focus #search_field': '_closeMobileMenu',
    },

    /**
     * Initialize the header.
     */
    initialize() {
        this._mobileMenuOpened = false;
        this._$window = $(window);
        this._$body = $(document.body);
        this._$navToggle = $('#nav_toggle');

        this._$mobileMenuMask = $('<div id="mobile_menu_mask"/>')
            .on('click touchstart', this._closeMobileMenu.bind(this))
            .insertAfter($('#mobile_navbar_container'));

        this._setupSearch();

        this._$window.on('resize', _.throttle(
            () => this._setMobileMode(this._$navToggle.is(':visible')),
            100));
    },

    /**
     * Handle a click on the mobile navigation menu.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    _handleNavClick(e) {
        e.stopPropagation();
        e.preventDefault();

        this._setMobileMenuOpened(!this._mobileMenuOpened);
    },

    /**
     * Set whether the header is in mobile mode.
     *
     * Args:
     *     inMobileMode (boolean):
     *         Whether the header should display in a mode suitable for mobile
     *         devices.
     */
    _setMobileMode(inMobileMode) {
        if (inMobileMode === this._inMobileMode) {
            return;
        }

        if (!inMobileMode) {
            this._setMobileMenuOpened(false);
        }

        this._inMobileMode = inMobileMode;
    },

    /**
     * Close the mobile menu.
     *
     * This is used as an event handler, to make it easy to close the
     * mobile menu and prevent any bubbling or default actions from the
     * event.
     */
    _closeMobileMenu() {
        this._setMobileMenuOpened(false);

        return false;
    },

    /**
     * Set up the search auto-complete field.
     */
    _setupSearch() {
        this._$search = $('#search_field').rbautocomplete({
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
                    if (data.summary.length < this.SEARCH_SUMMARY_TRIM_LEN) {
                        s = data.summary;
                    } else {
                        s = data.summary.substring(
                            0, this.SEARCH_SUMMARY_TRIM_LEN);
                    }

                    s += ` <span>(${_.escape(data.id)})</span>`;
                }

                return s;
            },
            matchCase: false,
            multiple: false,
            clickToURL: true,
            selectFirst: false,
            width: this.DESKTOP_SEARCH_RESULTS_WIDTH,
            enterToURL: true,
            resultsParentEl: $('#page-container'),
            resultsClass: 'ui-autocomplete-results search-results',
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
                                value: value[key],
                                result: value[key],
                            });
                        } else if (value.public) {
                            /*
                             * For review requests, only show ones that are
                             * public.
                             */
                            parsed.push({
                                data: value,
                                value: value[key],
                                result: value[key],
                            });
                        }
                    }
                }

                return parsed;
            },
            url: `${SITE_ROOT}api/search/`,
        });
    },

    /**
     * Set whether the mobile menu is opened.
     *
     * Args:
     *     opened (boolean):
     *         Whether the menu is open.
     */
    _setMobileMenuOpened(opened) {
        if (opened === this._mobileMenuOpened) {
            return;
        }

        if (opened) {
            this._$mobileMenuMask.show();
            _.defer(() => this._$body.addClass('mobile-menu-open'));
        } else {
            this._$body.removeClass('mobile-menu-open');
            _.delay(() => this._$mobileMenuMask.hide(), 300);
        }

        this._mobileMenuOpened = opened;
    },
});
