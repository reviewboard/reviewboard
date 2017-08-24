/**
 * A view which ensures that the specified elements are vertically centered.
 */
RB.CenteredElementManager = Backbone.View.extend({
    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options passed to this view.
     *
     * Option Args:
     *     elements (Array, optional):
     *         An initial array of elements to center.
     */
    initialize(options={}) {
        this._elements = options.elements || new Map();
        this._$window = $(window);

        this._updatePositionThrottled = _.throttle(() => this.updatePosition(),
                                                   10);

        this._$window.on('resize', this._updatePositionThrottled);
        this._$window.on('scroll', this._updatePositionThrottled);
    },

    /**
     * Remove the CenteredElementManager.
     *
     * This will result in the event handlers being removed.
     */
    remove() {
        Backbone.View.prototype.remove.call(this);

        this._$window.off('resize', this._updatePositionThrottled);
        this._$window.off('scroll', this._updatePositionThrottled);
    },

    /**
     * Set the elements and their containers.
     *
     * Args:
     *     elements (Map<Element, Element or jQuery>):
     *         The elements to center within their respective containers.
     */
    setElements(elements) {
        this._elements = elements;
    },

    /**
     * Update the position of the elements.
     *
     * This should only be done when the set of elements changed, as the view
     * will handle updating on window resizing and scrolling.
     */
    updatePosition() {
        if (this._elements.size === 0) {
            return;
        }

        const windowTop = this._$window.scrollTop();
        const windowHeight = this._$window.height();
        const windowBottom = windowTop + windowHeight;

        this._elements.forEach((containers, el) => {
            const $el = $(el);
            const $topContainer = containers.$top;
            const $bottomContainer = containers.$bottom || $topContainer;
            const containerTop = $topContainer.offset().top;
            const containerBottom = $bottomContainer.offset().top +
                                    $bottomContainer.height();

            /*
             * We don't have to vertically center the element when its
             * container is not on screen.
             */
            if (containerTop < windowBottom && containerBottom > windowTop) {
                /*
                 * When a container takes up the entire viewport, we can switch
                 * the CSS to use position: fixed. This way, we do not have to
                 * re-compute its position.
                 */
                if (windowTop >= containerTop &&
                    windowBottom <= containerBottom) {
                    if ($el.css('position') !== 'fixed') {
                        $el.css({
                            position: 'fixed',
                            left: $el.offset().left,
                            top: Math.round(
                                (windowHeight - $el.outerHeight()) / 2),
                        });
                    }
                } else {
                    const top = Math.max(windowTop, containerTop);
                    const bottom = Math.min(windowBottom, containerBottom);
                    const elTop = top - containerTop + Math.round(
                        (bottom - top - $el.outerHeight()) / 2);

                    $el.css({
                        position: 'absolute',
                        left: '',
                        top: elTop,
                    });
                }
            }
        });
    },
});
