/**
 * An infobox pop-up.
 *
 * This binds to an ``<a>`` element (expected to be either a bug or a user,
 * right now), and loads the contents of the infobox from a URL built from that
 * element's ``href`` attribute plus the string "infobox/".
 */
RB.InfoboxView = Backbone.View.extend({
    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     $target (jQuery):
     *         The target ``<a>`` element to watch.
     */
    initialize(options) {
        Backbone.View.prototype.initialize.call(this, options);

        this._$target = options.$target;
        this._timeout = null;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.InfoboxView:
     *     This object, for chaining.
     */
    render() {
        this._$target.on('mouseover', () => {
            this._timeout = setTimeout(() => this.fetch());
        });

        $([this._$target[0], this.$el[0]]).on({
            mouseover: () => {
                if (this.$el.is(':visible')) {
                    clearTimeout(this._timeout);
                }
            },
            mouseout: () => {
                clearTimeout(this._timeout);

                if (this.$el.is(':visible')) {
                    this._timeout = setTimeout(() => this.$el.fadeOut(),
                                               RB.InfoboxView.HIDE_DELAY_MS);
                }
            }
        });

        this.$el.hide();

        return this;
    },

    /**
     * Fetch the contents of the infobox and display it.
     */
    fetch() {
        const url = `${this._$target.attr('href')}infobox/`;
        const haveOldData = url in RB.InfoboxView.cache;

        if (haveOldData) {
            /*
             * If we have cached data, show that immediately and update once we
             * have the result from the server.
             */
            this._show(RB.InfoboxView.cache[url], true);
        }

        $.ajax(url, {
            ifModified: true
        }).done(responseText => {
            RB.InfoboxView.cache[url] = responseText;
            this._show(responseText, !haveOldData);
        });
    },

    /**
     * Show the given data in the infobox.
     *
     * Args:
     *     data (string):
     *         HTML to show in the infobox.
     *
     *     popup (boolean):
     *         Whether the infobox is being newly popped-up. If this is true,
     *         the box will position itself and animate. If not, only the
     *         contents will be updated.
     */
    _show(data, popup) {
        this.$el.html(data);

        if (popup) {
            this.$el
                .positionToSide(this._$target, {
                    side: 'tb',
                    xOffset: RB.InfoboxView.OFFSET_LEFT,
                    yDistance: RB.InfoboxView.OFFSET_TOP,
                    fitOnScreen: true
                })
                .fadeIn();
        }

        const $localTime = this.$('.localtime').children('time');

        if ($localTime.length) {
            const timezone = $localTime.data('timezone');
            const now = moment.tz(timezone);

            $localTime.text(now.format('LT'));
        }

        this.$('.timesince').timesince();
    }
}, {
    POPUP_DELAY_MS: 500,
    HIDE_DELAY_MS: 300,
    OFFSET_LEFT: -20,
    OFFSET_TOP: 10,

    cache: {}
});
