/**
 * Manages behavior and UI related to scrolling the page.
 *
 * This can be used by the UI to track pending and completed updates to
 * elements that might affect the current scroll position, such as new content
 * being injected into the DOM or being hidden/shown. When such updates occur
 * that would cause a page jump, the scroll manager will fix the scroll
 * position to counteract the jump.
 *
 * When a view is ready to make a DOM change that would impact the display or
 * size of an element, it should call
 * :js:func:`RB.ScrollManagerView.markForUpdate` before updating the element.
 * After, it should call :js:func:`RB.ScrollManagerView.markUpdates`.
 *
 * Views that create floating elements at the top of the page (such as banners)
 * should increment :js:attr:`RB.ScrollManagerView.scrollYOffset` by the height
 * of the element, and decrement it when the element goes away. This will
 * ensure that when navigating to an element through the scroll manager that
 * the height of the floating element will be taken into consideration for
 * the positioning.
 *
 * Attributes:
 *     scrollYOffset (number):
 *         The offset to add when scrolling to a target element or position.
 *         Callers should only increment or decrement this, and should never
 *         set it directly.
 */
RB.ScrollManagerView = Backbone.View.extend({
    /**
     * Initialize the scroll manager.
     */
    initialize() {
        this.scrollYOffset = 0;

        // This is used so that unit tests can create a dummy window.
        this.window = window;

        this._updateScrollPosScheduled = false;
        this._pendingElements = new Map();
        this._elements = new Map();
        this._oldScrollY = null;
        this._useScrollYOffset = false;
    },

    /**
     * Scroll to a specific element on the page.
     *
     * This will take the scroll offset into account.
     *
     * Args:
     *     $el (jQuery):
     *         The element to scroll to.
     */
    scrollToElement($el) {
        this.scrollToPosition($el.offset().top);
    },

    /**
     * Scroll to a specific position on the page.
     *
     * This will take the scroll offset into account.
     *
     * Args:
     *     scrollY (number):
     *         The Y position to scroll to.
     */
    scrollToPosition(scrollY) {
        this._oldScrollY = scrollY;

        /*
         * We use this instead of a flag being passed around to functions
         * because we might actually end up using a pre-scheduled update to
         * the scroll position, rather than scheduling a new one.
         */
        this._useScrollYOffset = true;

        /* Attempt to immedialely scroll to the desired position. */
        this.window.scrollTo(this.window.pageXOffset, scrollY);

        /*
         * Chrome (and possibly other browsers in the future) attempt to be
         * smart about restoring the initial scroll position after the page
         * has fully loaded. However, we want to control the position in this
         * case (probably in response to something in the URL we're handling),
         * so we want to disable Chrome's behavior. Fortunately, there's an
         * API for that.
         */
        if ('scrollRestoration' in history) {
            history.scrollRestoration = 'manual';
        }

        this._scheduleUpdateScrollPos(true);
    },

    /**
     * Mark an element for update.
     *
     * This should be called when an element will be updated with new
     * content/size/visibility. The current state of the element will be
     * tracked. When the update has finished, :js:func:`markUpdated` should
     * be called to finalize the update.
     *
     * Args:
     *     $el (jQuery):
     *         The element being updated.
     */
    markForUpdate($el) {
        console.assert($el.length === 1);

        const oldOffset = $el.offset();

        this._pendingElements.set($el[0], {
            oldHeight: $el.outerHeight(),
            oldOffset: {
                left: oldOffset.left,
                top: oldOffset.top,
            },
        });

        if (this._oldScrollY === null) {
            this._oldScrollY = this.window.pageYOffset;
        }
    },

    /**
     * Mark an element as having been updated.
     *
     * This will schedule a scroll position update, factoring in the size
     * and position differences for the element and helping prevent a page
     * jump if the update occurred before the current scroll position.
     *
     * Args:
     *     $el (jQuery):
     *         The element that was updated.
     */
    markUpdated($el) {
        console.assert($el.length === 1);

        const el = $el[0];
        const elInfo = this._pendingElements.get(el);

        if (elInfo) {
            elInfo.newHeight = $el.outerHeight();
            elInfo.newOffset = $el.offset();

            this._elements.set(el, elInfo);
            this._pendingElements.delete(el);
        }

        this._scheduleUpdateScrollPos();
    },

    /**
     * Schedule an update for the scroll position.
     *
     * This will schedule the scroll position to be updated to take into
     * account any updated elements. The update will happen in the next
     * available animation frame. Only one will ever be scheduled at a time.
     */
    _scheduleUpdateScrollPos() {
        if (!this._updateScrollPosScheduled) {
            this._updateScrollPosScheduled = true;

            /*
             * Ideally we would update the DOM and set the scroll position at
             * the same time, synchronized, without waiting for an animation
             * frame and preventing any kind of a jump. This would work okay
             * in some browsers (Chrome and Firefox are pretty good at not
             * jumping), but some -- Safari (as of 10.1), Internet Explorer
             * (as of 11), and Edge (as of 38.14393) -- will still jump after
             * our code executes.
             *
             * We can minimize that jump by performing the scroll update during
             * an animation frame, getting it as close as possible to the DOM
             * layout update.
             */
            this.window.requestAnimationFrame(
                this._updateScrollPos.bind(this));
        }
    },

    /**
     * Update the scroll position to factor in any element updates.
     *
     * This will look for any tracked elements that have been updated
     * earlier in the page (before the current scroll position). It will
     * then update the scroll position to take those updates into account,
     * helping prevent a page jump.
     */
    _updateScrollPos() {
        const elInfos = [];

        this._elements.forEach((elInfo, el) => {
            /*
             * Check if the element remained the same size. We can ignore
             * these.
             */
            if (elInfo.oldHeight !== elInfo.newHeighht) {
                elInfo.el = el;
                elInfos.push(elInfo);
            }
        });

        let scrollY = this._oldScrollY;

        if (this._useScrollYOffset) {
            scrollY -= this.scrollYOffset;
        }

        if (elInfos.length > 0) {
            /* Try to put these in order by position. */
            elInfos.sort((a, b) => a.newOffset.top - b.newOffset.top);

            for (let i = 0; i < elInfos.length; i++) {
                const elInfo = elInfos[i];

                /* Check if the element precedes the current scroll position. */
                if (elInfo.newOffset.top + elInfo.newHeight < scrollY) {
                    scrollY += (elInfo.newHeight - elInfo.oldHeight) +
                               (elInfo.newOffset.top - elInfo.oldOffset.top);
                }
            }
        }

        this.window.scrollTo(this.window.pageXOffset, scrollY);

        this._elements.clear();
        this._oldScrollY = null;
        this._useScrollYOffset = false;
        this._updateScrollPosScheduled = false;
    },
});


RB.scrollManager = new RB.ScrollManagerView();
