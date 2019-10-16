/**
 * Show the current support status for the Review Board install.
 */
RB.SupportBannerView = Backbone.View.extend({
    _loadingHTML: _.template(dedent`
        <h2><%- titleText %></h2>
        <p><span class="fa fa-spin fa-spinner"></span></p>
    `)({
        titleText: gettext('Retrieving support information...'),
    }),

    _errorHTML: _.template(dedent`
        <h2><%- titleText %></h2>
        <p><%- bodyText %></p>
        <p><%= fileText %></p>
    `)({
        titleText: gettext('Failed to retrieve support information'),
        bodyText: gettext('We could not communicate with the Beanbag, Inc. server to retrieve your support information. You may be behind a firewall or have no Internet access.'),
        fileText: gettext('You may file an issue on our <a href="https://reviewboard.googlegroups.com">community support tracker.</a>'),
    }),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options passed to the view.
     *
     * Option Args:
     *     supportData (string):
     *         An encoded payload containing information used to look up
     *         information on an active support contract for the server.
     */
    initialize(options) {
        const now = new Date();

        console.assert(RB.SupportBannerView.instance === null);
        RB.SupportBannerView.instance = this;

        _.bindAll(this, '_onError');

        window.addEventListener('error', this._onError, true);

        this._script = $('<script />')
            .attr('src', RB.SupportBannerView.supportURL + '?' + $.param({
                'support-data': options.supportData,
                callback: 'RB.SupportBannerView.instance.receive',
                _: now.valueOf(),  // Cache bust.
            }))
            .get(0);

        /*
         * If we use jQuery's appendTo, we end up with two <script> tags being
         * added to the document.
         */
        document.body.appendChild(this._script);

    },

    /**
     * Handle a DOM error.
     *
     * If the specified error targets the script tag (e.g., if it could not
     * be loaded), then an error will be displayed in the banner
     *
     * Args:
     *     e (Event):
     *         The event that triggered this function.
     */
    _onError(e) {
        if (e.target === this._script) {
            this.render({
                html: this._errorHTML,
                className: 'error',
            });

            window.removeEventListener('error', this._onError, true);
        }
    },

    /**
     * Render the view
     *
     * Args:
     *     options (object):
     *         The rendering options.
     *
     * Option Args:
     *     html (string)
     *         The html to render in the banner.
     *
     *     className (string):
     *         The name of the class to add to the banner.
     */
    render(options) {
        options = _.extend({
            className: 'loading',
            html: this._loadingHTML,
        }, options);

        this.$el
            .empty()
            .html(options.html)
            .attr('class', options.className);

        return this;
    },

    /**
     * Receive the data from the server.
     *
     * This is invoked via a JSONP callback.
     *
     * Args:
     *     options (object):
     *         The options received from the server.
     *
     * Option Args:
     *     supportLevel (string):
     *         The level of support the server has.
     *
     *     html (string):
     *         The HTML to render in the banner.
     */
    receive(options) {
        window.removeEventListener('error', this._onError, true);

        this.render({
            className: options.supportLevel + '-support',
            html: options.html,
        });
    },
}, {
    instance: null,
    supportURL: 'https://www.beanbaginc.com/support/reviewboard/_status/',
});
