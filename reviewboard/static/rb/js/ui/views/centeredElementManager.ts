/**
 * A view which ensures that the specified elements are vertically centered.
 */

import { BaseView, spina } from '@beanbag/spina';


/** Stored data about a centered element. */
type CenteredElementData = {
    /** The element at the top of the region to center in. */
    $top: JQuery;

    /** The parent of the element to center. */
    $parent?: JQuery;

    /** The element at the bottom of the region to center in. */
    $bottom?: JQuery;
}

/** Map from a centered element to necessary data. */
type CenteredElements = Map<HTMLElement, CenteredElementData>;


/**
 * Options for the CenteredElementManager view.
 *
 * Version Added:
 *     7.0
 */
export interface CenteredElementManagerOptions {
    /** Information about which elements to center. */
    elements?: CenteredElements;
}


/**
 * A view which ensures that the specified elements are vertically centered.
 */
@spina
export class CenteredElementManager extends BaseView<
    undefined,
    HTMLElement,
    CenteredElementManagerOptions
> {
    /**********************
     * Instance variables *
     **********************/

    /**
     * The elements being centered.
     *
     * This is public for consumption in unit tests.
     */
    _elements: CenteredElements;

    /** A function to throttle postion updates. */
    #updatePositionThrottled: () => void;

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
    initialize(
        options: Backbone.CombinedViewConstructorOptions<
            CenteredElementManagerOptions, undefined, HTMLElement> = {},
    ) {
        this.#updatePositionThrottled = () => {
            requestAnimationFrame(() => this.updatePosition());
        };

        this.setElements(options.elements ||
                         new Map<HTMLElement, CenteredElementData>());
    }

    /**
     * Remove the CenteredElementManager.
     *
     * This will result in the event handlers being removed.
     *
     * Returns:
     *     CenteredElementManager:
     *     This object, for chaining.
     */
    remove(): this {
        super.remove();

        this.setElements(new Map<HTMLElement, CenteredElementData>());

        return this;
    }

    /**
     * Set the elements and their containers.
     *
     * Args:
     *     elements (Map<Element, CenteredElementData>):
     *         The elements to center within their respective containers.
     */
    setElements(elements: CenteredElements) {
        this._elements = elements;

        if (elements.size > 0) {
            $(window).on('resize scroll', this.#updatePositionThrottled);
        } else {
            $(window).off('resize scroll', this.#updatePositionThrottled);
        }
    }

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
    }
}
