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
     *
     * Args:
     *     options (object, optional):
     *         Options for the view.
     *
     * Option Args:
     *     $body (jQuery, optional):
     *         The body element. This is useful for unit tests.
     *
     *     $pageSidebar (jQuery, optional):
     *         The page sidebar element. This is useful for unit tests.
     */
    initialize(options={}) {
        if (RB.HeaderView.instance !== null) {
            console.warn('There are two instances of RB.HeaderView on the ' +
                         'page. Make sure only one RB.PageView is ' +
                         'instantiated and registered through ' +
                         'RB.PageManager.setupPage().');
        } else {
            RB.HeaderView.instance = this;
        }

        this.options = options;

        /*
         * This is used by RB.PageManager to determine if a RB.PageView
         * subclass has correctly rendered a HeaderView, or if PageManager
         * needs to take care of it.
         *
         * This is deprecated and can be removed in Review Board 5.0.
         */
        this.isRendered = false;

        this._mobileMenuOpened = false;

        this._$window = null;
        this._$body = null;
        this._$navToggle = null;
        this._$mobileMenuMask = null;
    },

    /**
     * Remove the view from the DOM and disable event handling.
     *
     * This will also unset :js:attr:`RB.HeaderView.instance`, if currently
     * set to this instance.
     */
    remove() {
        if (RB.HeaderView.instance === this) {
            RB.HeaderView.instance = null;
        }

        if (this._$window) {
            this._$window.off('resize.rbHeaderView');
        }

        Backbone.View.prototype.remove.call(this);
    },

    /**
     * Render the header.
     *
     * Returns:
     *     RB.HeaderView:
     *     This view, for chaining.
     */
    render() {
        const options = this.options;

        this._$window = $(window);
        this._$body = options.body || $(document.body);
        this._$navToggle = $('#nav_toggle');
        this._$mobileMenuMask = $('<div id="mobile_menu_mask"/>')
            .on('click touchstart', this._closeMobileMenu.bind(this))
            .insertAfter(options.$pageSidebar || $('#page-sidebar'));

        this._$window.on('resize.rbHeaderView', _.throttle(
            this._recalcMobileMode.bind(this),
            100));
        this._recalcMobileMode();

        this._setupSearch();

        this.isRendered = true;

        return this;
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
     * Recalculate whether the header and nav menu is in mobile mode.
     */
    _recalcMobileMode() {
        const inMobileMode = this._$navToggle.is(':visible');

        if (inMobileMode === this.inMobileMode) {
            return;
        }

        if (!inMobileMode) {
            this._setMobileMenuOpened(false);
        }

        this.inMobileMode = inMobileMode;
        this.trigger('mobileModeChanged', inMobileMode);
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
            _.defer(() => this._$body.addClass('js-mobile-menu-open'));
        } else {
            this._$body.removeClass('js-mobile-menu-open');
            _.delay(() => this._$mobileMenuMask.hide(), 300);
        }

        this._mobileMenuOpened = opened;
    },
}, {
    /** The instance of the HeaderView. */
    instance: null,
});
