/*
 * Manages a collection of configuration pages.
 *
 * The primary job of this view is to handle sub-page navigation.
 * The actual page will contain several "pages" that are shown or hidden
 * depending on what the user has clicked on the sidebar.
 */
Djblets.Config.PagesView = Backbone.View.extend({
    /*
     * Initializes the view.
     *
     * This will set up the router for handling page navigation.
     */
    initialize: function() {
        this.router = new Backbone.Router({
            routes: {
                ':pageID': 'page'
            }
        });
        this.listenTo(this.router, 'route:page', this._onPageChanged);

        this._$activeNav = null;
        this._$activePage = null;
        this._preserveMessages = true;
    },

    /*
     * Renders the view.
     *
     * This will set the default page to be shown, and instruct Backbone
     * to begin handling the routing.
     */
    render: function() {
        this._$pageNavs = this.$('.config-forms-side-nav li');
        this._$pages = this.$('.config-forms-page-content > .page');

        this._$activeNav = this._$pageNavs.eq(0).addClass('active');
        this._$activePage = this._$pages.eq(0).addClass('active');

        Backbone.history.start({
            root: window.location
        });

        return this;
    },

    /*
     * Handler for when the page changed.
     *
     * The sidebar will be updated to reflect the current active page,
     * and the page will be shown.
     *
     * If navigating pages manually, any messages provided by the backend
     * form will be removed. We don't do this the first time there's a
     * navigation, as this will be called when first rendering the view.
     */
    _onPageChanged: function(pageID) {
        this._$activeNav.removeClass('active');
        this._$activePage.removeClass('active');

        this._$activePage = $('#page_' + pageID);

        if (this._$activePage.length === 0) {
            /*
             * If the requested page doesn't exist (for example, it might be
             * hidden, or just typoed), load the first page instead.
             */
            this.router.navigate(
                this._$pageNavs.find('a').attr('href').substr(1),
                {
                    trigger: true,
                    replace: true
                });
        } else {
            this._$activeNav =
                this._$pageNavs.filter(':has(a[href=#' + pageID + '])')
                    .addClass('active');

            this._$activePage.addClass('active');

            if (!this._preserveMessages) {
                $('#messages').remove();
            }

            this._preserveMessages = false;
        }
    }
});
