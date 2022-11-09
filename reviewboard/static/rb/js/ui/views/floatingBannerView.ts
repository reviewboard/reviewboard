import { BaseView, spina } from '@beanbag/spina';


/**
 * Options for the FloatingBannerView.
 *
 * Version Added:
 *     6.0
 */
export interface FloatingBannerViewOptions {
    /**
     * The container to use when the banner is floating.
     */
    $floatContainer: JQuery;

    /**
     * The class name used when the banner is not floating.
     */
    noFloatContainerClass: string;
}


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
@spina
export class FloatingBannerView<
    TModel extends (Backbone.Model | undefined) = Backbone.Model,
    TElement extends Element = HTMLElement,
    TExtraViewOptions = FloatingBannerViewOptions
> extends BaseView<
    TModel,
    TElement,
    TExtraViewOptions
> {
    /**********************
     * Instance variables *
     **********************/
    #$floatContainer: JQuery = null;
    #$floatSpacer: JQuery = null;
    #noFloatContainerClass: string = null;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (FloatingBannerViewOptions):
     *         Options for the view.
     */
    initialize(options) {
        super.initialize(options);

        this.#$floatContainer = options.$floatContainer;
        this.#noFloatContainerClass = options.noFloatContainerClass;
    }

    /**
     * Render the banner and listens for scroll and resize updates.
     */
    onInitialRender() {
        $(window)
            .scroll(() => this.#updateFloatPosition())
            .resize(() => this.#updateSize());
        _.defer(() => this.#updateFloatPosition());
    }

    /**
     * Remove the view from the DOM.
     *
     * This will remove both the banner and the floating spacer (if currently
     * in the DOM).
     *
     * Returns:
     *     FloatingBannerView:
     *     This object, for chaining.
     */
    remove(): this {
        if (this.#$floatSpacer !== null) {
            this.#$floatSpacer.remove();
            this.#$floatSpacer = null;
        }

        super.remove();

        return this;
    }

    /**
     * Update the size of the banner to match the spacer.
     */
    #updateSize() {
        if (this.#$floatSpacer !== null) {
            if (this.$el.hasClass('floating')) {
                const rect =
                    this.#$floatSpacer.parent()[0].getBoundingClientRect();

                this.$el.width(
                    Math.ceil(rect.width) -
                    Math.max(this.$el.getExtents('bpm', 'lr'), 0));
            } else {
                this.$el.width('auto');
            }
        }
    }

    /**
     * Update the position of the banner.
     *
     * This will factor in how much of the container is visible, based on
     * its size, position, and the scroll offset. It will then attempt
     * to position the banner to the top of the visible portion of the
     * container.
     */
    #updateFloatPosition() {
        if (this.$el.parent().length === 0) {
            return;
        }

        if (this.#$floatSpacer === null) {
            this.#$floatSpacer = this.$el.wrap($('<div/>')).parent();
            this.#updateSize();
        }

        const containerTop = this.#$floatContainer.offset().top;
        const containerHeight = this.#$floatContainer.outerHeight();
        const containerBottom = containerTop + containerHeight;
        const windowTop = $(window).scrollTop();
        const topOffset = this.#$floatSpacer.offset().top - windowTop;
        const outerHeight = this.$el.outerHeight(true);
        const wasFloating = this.$el.hasClass('floating');

        if (!this.#$floatContainer.hasClass(this.#noFloatContainerClass) &&
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
                this.#$floatSpacer
                    .height(this.$el.outerHeight())
                    .css({
                        'margin-bottom': this.$el.css('margin-bottom'),
                        'margin-top': this.$el.css('margin-top'),
                    });

                this.$el
                    .addClass('floating')
                    .css({
                        'margin-top': 0,
                        'position': 'fixed',
                    });
            }

            this.$el.css('top',
                         windowTop > containerBottom - outerHeight
                         ? containerBottom - outerHeight - windowTop
                         : 0);

            this.#updateSize();
        } else if (wasFloating) {
            /*
             * We're now longer floating. Unset the styles on the banner and
             * on the spacer (in order to prevent the spacer from taking up
             * any additional room.
             */
            this.$el
                .removeClass('floating')
                .css({
                    'margin-top': '',
                    'position': '',
                    'top': '',
                });
            this.#$floatSpacer
                .height('auto')
                .css('margin', 0);
        }
    }
}
