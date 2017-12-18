/**
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
    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     $floatContainer (jQuery):
     *         The container to use when the banner is floating.
     *
     *     noFloatContainerClass (string):
     *         The class name used when the banner should not be floating.
     */
    initialize(options) {
        this.options = options;
        this._$floatSpacer = null;

        _.bindAll(this, '_updateFloatPosition', '_updateSize');
    },

    /**
     * Render the banner and listens for scroll and resize updates.
     *
     * Returns:
     *     RB.FloatingBannerView:
     *     This object, for chaining.
     */
    render() {
        $(window)
            .scroll(this._updateFloatPosition)
            .resize(this._updateSize);
        _.defer(this._updateFloatPosition);

        return this;
    },

    /**
     * Remove the view from the DOM.
     *
     * This will remove both the banner and the floating spacer (if currently
     * in the DOM).
     */
    remove() {
        if (this._$floatSpacer !== null) {
            this._$floatSpacer.remove();
        }

        Backbone.View.prototype.remove.call(this);
    },

    /**
     * Update the size of the banner to match the spacer.
     */
    _updateSize() {
        if (this._$floatSpacer !== null) {
            if (this.$el.hasClass('floating')) {
                const rect =
                    this._$floatSpacer.parent()[0].getBoundingClientRect();

                this.$el.width(
                    Math.ceil(rect.width) -
                    this.$el.getExtents('bpm', 'lr'));
            } else {
                this.$el.width('auto');
            }
        }
    },

    /**
     * Update the position of the banner.
     *
     * This will factor in how much of the container is visible, based on
     * its size, position, and the scroll offset. It will then attempt
     * to position the banner to the top of the visible portion of the
     * container.
     */
    _updateFloatPosition() {
        if (this.$el.parent().length === 0) {
            return;
        }

        if (this._$floatSpacer === null) {
            this._$floatSpacer = this.$el.wrap($('<div/>')).parent();
            this._updateSize();
        }

        const $container = this.options.$floatContainer;
        const containerTop = $container.offset().top;
        const containerHeight = $container.outerHeight();
        const containerBottom = containerTop + containerHeight;
        const windowTop = $(window).scrollTop();
        const topOffset = this._$floatSpacer.offset().top - windowTop;
        const outerHeight = this.$el.outerHeight(true);

        const wasFloating = this.$el.hasClass('floating');

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
                        'margin-bottom': this.$el.css('margin-bottom'),
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
                    position: '',
                });
            this._$floatSpacer
                .height('auto')
                .css('margin', 0);
        }
    },
});
