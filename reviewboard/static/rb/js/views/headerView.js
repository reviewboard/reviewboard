/*
 * Site Header
 */
RB.HeaderView = Backbone.View.extend({
    SEARCH_SUMMARY_TRIM_LEN: 28,
    DESKTOP_SEARCH_RESULTS_WIDTH: 350,

    events: {
        'click #nav_toggle': '_handleNavClick',
        'touchstart #nav_toggle': '_handleNavClick',
        'focus #search_field': '_closeMobileMenu'
    },

    /*
     * Initializes the header.
     */
    initialize: function() {
        this._mobileMenuOpened = false;
        this._$window = $(window);
        this._$body = $(document.body);
        this._$navToggle = $('#nav_toggle');

        this._$mobileMenuMask = $('<div id="mobile_menu_mask"/>')
            .on('click touchstart', _.bind(this._closeMobileMenu, this))
            .insertAfter($('#mobile_navbar_container'));

        this._setupSearch();

        this._$window.on('resize', _.throttle(_.bind(function() {
            this._setMobileMode(this._$navToggle.is(':visible'));
        }, this), 100));
    },

    _handleNavClick: function(e) {
        e.stopPropagation();
        e.preventDefault();

        this._setMobileMenuOpened(!this._mobileMenuOpened);
    },

    _setMobileMode: function(inMobileMode) {
        if (inMobileMode === this._inMobileMode) {
            return;
        }

        if (!inMobileMode) {
            this._setMobileMenuOpened(false);
        }

        this._inMobileMode = inMobileMode;
    },

    /*
     * Closes the mobile menu.
     *
     * This is used as an event handler, to make it easy to close the
     * mobile menu and prevent any bubbling or default actions from the
     * event.
     */
    _closeMobileMenu: function() {
        this._setMobileMenuOpened(false);

        return false;
    },

    /*
     * Sets up the search auto-complete field.
     */
    _setupSearch: function() {
        this._$search = $('#search_field').rbautocomplete({
            formatItem: _.bind(function(data) {
                var s;

                if (data.username) {
                    // For the format of users
                    s = data.username;

                    if (data.fullname) {
                        s += " <span>(" + _.escape(data.fullname) + ")</span>";
                    }

                } else if (data.name) {
                    // For the format of groups
                    s = data.name;
                    s += " <span>(" + _.escape(data.display_name) + ")</span>";
                } else if (data.summary) {
                    // For the format of review requests
                    if (data.summary.length < this.SEARCH_SUMMARY_TRIM_LEN) {
                        s = data.summary;
                    } else {
                        s = data.summary.substring(
                            0, this.SEARCH_SUMMARY_TRIM_LEN);
                    }

                    s += " <span>(" + _.escape(data.id) + ")</span>";
                }

                return s;
            }, this),
            matchCase: false,
            multiple: false,
            clickToURL: true,
            selectFirst: false,
            width: this.DESKTOP_SEARCH_RESULTS_WIDTH,
            enterToURL: true,
            resultsParentEl: $('#page-container'),
            resultsClass: 'ui-autocomplete-results search-results',
            parse: function(data) {
                var jsonData = data,
                    jsonDataSearch = jsonData.search,
                    parsed = [],
                    objects = ["users", "groups", "review_requests"],
                    values = ["username", "name", "summary"],
                    value,
                    items,
                    i,
                    j;

                for (j = 0; j < objects.length; j++) {
                    items = jsonDataSearch[objects[j]];

                    for (i = 0; i < items.length; i++) {
                        value = items[i];

                        if (j !== 2) {
                            parsed.push({
                                data: value,
                                value: value[values[j]],
                                result: value[values[j]]
                            });
                        } else if (value['public']) {
                            // Only show review requests that are public
                            value.url = SITE_ROOT + "r/" + value.id;
                            parsed.push({
                                data: value,
                                value: value[values[j]],
                                result: value[values[j]]
                            });
                        }
                    }
                }

                return parsed;
            },
            url: SITE_ROOT + "api/" + "search/"
        });
    },


    /*
     * Set whether the mobile menu is opened.
     */
    _setMobileMenuOpened: function(opened) {
        if (opened === this._mobileMenuOpened) {
            return;
        }

        if (opened) {
            this._$mobileMenuMask.show();

            _.defer(_.bind(function() {
                this._$body.addClass('mobile-menu-open');
            }, this));
        } else {
            this._$body.removeClass('mobile-menu-open');

            _.delay(_.bind(function() {
                this._$mobileMenuMask.hide();
            }, this), 300);
        }

        this._mobileMenuOpened = opened;
    }
});
