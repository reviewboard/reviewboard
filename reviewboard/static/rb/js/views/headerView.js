/*
 * Site Header
 */
RB.HeaderView = Backbone.View.extend({
    MOBILE_MENU_MAX_WIDTH: 720,

    events: {
        'click #logo': '_handleLogoClick',
        'click #search-icon': '_toggleSearchBar'
    },

    /*
     * Initializes the header.
     */
    initialize: function() {
        this._mobileMenuOpened = false;
        this._$window = $(window);

        this._$window.on('resize', _.throttle(_.bind(function() {
            if (this._$window.width() > this.MOBILE_MENU_MAX_WIDTH) {
                this._closeMobileMenu();
            }
        }, this), 100));

        this._$mobileMenuMask = $('#mobile-menu-mask')
            .click(_.bind(this._closeMobileMenu, this));
        this._$navbarContainer = $('#navbar-container');
        this._$body = $('body');
    },

    _handleLogoClick: function() {
        if (this._$window.width() <= this.MOBILE_MENU_MAX_WIDTH) {
            this._mobileMenuToggle(
                !$('#navbar-container').hasClass('menu-active'));
        } else {
            window.location.href = SITE_ROOT;
        }
    },

    _toggleSearchBar: function() {
        this.$('#search').toggle();
    },

    _closeMobileMenu: function() {
        this._mobileMenuToggle(false);
    },

    /*
     * Mobile Menu toggle for Navbar.
     * This will control the open and close of mobile navbar menu and menu mask
     *
     * @param {bool} toggle   To open or close the menu
     */
    _mobileMenuToggle: function(toggle) {
        if (toggle === this._mobileMenuOpened) {
            return;
        }

        if (toggle) {
            this._$navbarContainer.animate({
                left: '0px'
            }, function() {
                $(this).addClass('menu-active');
            });

            this._$mobileMenuMask
                .css('opacity', 0)
                .show()
                .animate({
                    opacity: 0.5
                });
            this._$body.css('overflow', 'hidden');
        } else {
            this._$body.css('overflow', '');
            this._$mobileMenuMask
                .animate({
                    opacity: 0
                }, function() {
                    $(this).hide();
                });

            this._$navbarContainer.animate({
                left: '-160px'
            }, function() {
                $(this).removeClass('menu-active');
            });
        }

        this._mobileMenuOpened = toggle;
    }
});
