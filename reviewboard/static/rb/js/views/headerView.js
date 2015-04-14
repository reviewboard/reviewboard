/*
 * Site Header
 */
RB.HeaderView = Backbone.View.extend({
    events: {
        'click #logo': '_handleLogoClick',
        'click #search-icon': '_toggleSearchBar'
    },

    /*
     * Initializes the header.
     */
    initialize: function() {
        var e = this;
        $(window).on("resize", _.throttle(function(){
            if ($(window).width() > 720) {
                e._closeMobileMenu();
            }
        }, 100));

        this._$mobileMenuMask = $('#mobile-menu-mask')
            .click(_.bind(this._closeMobileMenu, this));
        this._$navbarContainer = $('#navbar-container');
        this._$body = $('body');
    },

    _handleLogoClick: function() {
        if ($(window).width() <= 720) {
            this._mobileMenuToggle(
                !$('#navbar-container').hasClass('menu-active'));
        } else {
            window.location.href = '/';
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
        if (toggle) {
            this._$navbarContainer.animate({
                left: '0px'
            }, function() {
                $(this).addClass('menu-active');
            });

            this._$mobileMenuMask.show();
            this._$body.css('overflow', 'hidden');
        } else {
            this._$body.css('overflow', 'auto');
            this._$mobileMenuMask.hide();

            this._$navbarContainer.animate({
                left: '-160px'
            }, function() {
                $(this).removeClass('menu-active');
            });
        }
    }
});
