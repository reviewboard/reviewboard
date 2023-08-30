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
        this._$window = $(window);

        this._updatePositionThrottled = () => {
            requestAnimationFrame(() => this.updatePosition());
        };

        this.setElements(options.elements || new Map());
    },

    /**
     * Remove the CenteredElementManager.
     *
     * This will result in the event handlers being removed.
     */
    remove() {
        Backbone.View.prototype.remove.call(this);

        this.setElements(new Map());
    },

    /**
     * Set the elements and their containers.
     *
     * Args:
     *     elements (Map<Element, Element or jQuery>):
     *         The elements to center within their respective containers.
     */
    setElements(elements) {
        const $window = this._$window;

        this._elements = elements;

        if (elements.size > 0) {
            $window.on('resize scroll', this._updatePositionThrottled);
        } else {
            $window.off('resize scroll', this._updatePositionThrottled);
        }
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

        const viewportTop = RB.contentViewport.get('top');
        const viewportBottom = RB.contentViewport.get('bottom');
        let windowTop = window.scrollY;
        const windowHeight = window.innerHeight;
        const windowBottom = windowTop + windowHeight - viewportBottom;

        windowTop += viewportTop;

        this._elements.forEach((containers, el) => {
            const $el = $(el);
            const $topContainer = containers.$top;
            const $parentContainer = containers.$parent || $topContainer;
            const $bottomContainer = containers.$bottom || $parentContainer;
            const containerTop = $topContainer.offset().top;
            const containerBottom =
                $bottomContainer.height() +
                ($bottomContainer === $topContainer
                 ? containerTop
                 : $bottomContainer.offset().top);

            /*
             * If the top container is above the element's parent container,
             * we'll need to offset the position later.
             */
            const topOffset =
                $parentContainer === $topContainer
                ? 0
                : $parentContainer.offset().top - containerTop;

            /*
             * We don't have to vertically center the element when its
             * container is not on screen.
             */
            if (containerTop >= windowBottom && containerBottom <= windowTop) {
                return;
            }

            const elStyle = getComputedStyle(el);
            const elHeight = el.offsetHeight;
            const posType = elStyle.position;
            let newCSS = null;
            let newTop = null;

            /*
             * When a container takes up the entire viewport, we can switch
             * the CSS to use position: fixed. This way, we do not have to
             * re-compute its position.
             */
            if (windowTop >= containerTop &&
                windowBottom <= containerBottom) {
                newTop =
                    viewportTop +
                    (windowHeight - viewportTop - viewportBottom -
                     elHeight) / 2;

                if (posType !== 'fixed') {
                    newCSS = {
                        left: $el.offset().left,

                        /* Ensure we're in control of placement. */
                        position: 'fixed',
                        right: 'auto',
                        transform: 'none',
                    };
                }
            } else {
                const top = Math.max(windowTop, containerTop);
                const bottom = Math.min(windowBottom, containerBottom);
                const availHeight = bottom - top - elHeight;
                const relTop = top - containerTop;

                /*
                 * Make sure the top and bottom never exceeds the
                 * calculated boundaries.
                 *
                 * We'll always position at least at 0, the top of the
                 * boundary.
                 *
                 * We'll cap at availHeight, the bottom of the boundary
                 * minus the element height.
                 *
                 * Optimistically, we'll position half-way through the
                 * boundary.
                 */
                newTop =
                    Math.max(
                        0,
                        relTop + Math.min(availHeight, availHeight / 2)) -
                    topOffset;

                if (posType === 'fixed') {
                    newCSS = {
                        position: 'absolute',

                        /* Clear these settings to restore defaults. */
                        left: '',
                        right: '',
                        transform: '',
                    };
                }
            }

            if (newCSS) {
                $el.css(newCSS);
            }

            if (Math.round(parseInt(elStyle.top)) !== Math.round(newTop)) {
                el.style.top = newTop + 'px';
            }
        });
    },
});
