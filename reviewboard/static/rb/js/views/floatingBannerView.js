/*
 * Floats a banner on screen within a container.
 *
 * The banner will appear at the top of the container, or the screen,
 * whichever is visible, until the container is no longer on-screen.
 *
 * The banner will keep a spacer in its original location at the top
 * of the container in order to reserve space for it to anchor to.
 * This ensures that the page doesn't jump too horribly.
 */
RB.FloatingBannerView = Backbone.View.extend({
    initialize: function() {
        this._$floatSpacer = null;

        _.bindAll(this, '_updateFloatPosition', '_updateSize');
    },

    /*
     * Renders the banner and listens for scroll and resize updates.
     */
    render: function() {
        $(window)
            .scroll(this._updateFloatPosition)
            .resize(this._updateSize);
        _.defer(this._updateFloatPosition);

        return this;
    },

    /*
     * Updates the size of the banner to match the spacer.
     */
    _updateSize: function() {
        if (this._$floatSpacer !== null) {
            this.$el.width(this._$floatSpacer.parent().width() -
                           this.$el.getExtents('bpm', 'lr'));
        }
    },

    /*
     * Updates the position of the banner.
     *
     * This will factor in how much of the container is visible, based on
     * its size, position, and the scroll offset. It will then attempt
     * to position the banner to the top of the visible portion of the
     * container.
     */
    _updateFloatPosition: function() {
        var $container,
            containerTop,
            windowTop,
            topOffset,
            outerHeight;

        if (this.$el.parent().length === 0) {
            return;
        }

        /*
         * Something about the below causes the "Publish" button to never
         * show up on IE8. Turn it into a fixed box on IE.
         */
        if ($.browser.msie) {
            return;
        }

        if (this._$floatSpacer === null) {
            this._$floatSpacer = this.$el.wrap($('<div/>')).parent();
            this._updateSize();
        }

        $container = this.options.$floatContainer;

        containerTop = $container.offset().top;
        windowTop = $(window).scrollTop();
        topOffset = this._$floatSpacer.offset().top - windowTop;
        outerHeight = this.$el.outerHeight();

        if (!$container.hasClass(this.options.noFloatContainerClass) &&
            topOffset < 0 &&
            containerTop < windowTop &&
            windowTop < (containerTop + $container.outerHeight() -
                         outerHeight)) {
            this.$el
                .addClass('floating')
                .css({
                    top: 0,
                    position: 'fixed'
                });

            this._updateSize();
        } else {
            this.$el
                .removeClass('floating')
                .css({
                    top: '',
                    position: ''
                });
        }
    }
});
