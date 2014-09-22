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
            containerBottom,
            containerHeight,
            wasFloating,
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
        containerHeight = $container.outerHeight();
        containerBottom = containerTop + containerHeight;
        windowTop = $(window).scrollTop();
        topOffset = this._$floatSpacer.offset().top - windowTop;
        outerHeight = this.$el.outerHeight(true);

        wasFloating = this.$el.hasClass('floating');

        if (!$container.hasClass(this.options.noFloatContainerClass) &&
            topOffset < 0 &&
            containerTop < windowTop &&
            windowTop < containerBottom) {
            /*
             * We're floating! If we just entered this state, set the
             * appropriate styles on the element.
             *
             * We'll then want to set the top to 0, unless the user is
             * scrolling the banner out of view. In that case, figure out how
             * much to show, and set the appropriate offset.
             */
            if (!wasFloating) {
                /*
                 * Set the spacer to be the dimensions of the docked banner,
                 * so that the container doesn't change sizes when we go into
                 * float mode.
                 */
                this._$floatSpacer
                    .height(this.$el.outerHeight())
                    .css({
                        'margin-top': this.$el.css('margin-top'),
                        'margin-bottom': this.$el.css('margin-bottom')
                    });

                this.$el
                    .addClass('floating')
                    .css('position', 'fixed');
            }

            this.$el.css('top',
                         windowTop > containerBottom - outerHeight
                         ? containerBottom - outerHeight - windowTop
                         : 0);

            this._updateSize();
        } else if (wasFloating) {
            /*
             * We're now longer floating. Unset the styles on the banner and
             * on the spacer (in order to prevent the spacer from taking up
             * any additional room.
             */
            this.$el
                .removeClass('floating')
                .css({
                    top: '',
                    position: ''
                });
            this._$floatSpacer
                .height('auto')
                .css('margin', 0);
        }
    }
});
