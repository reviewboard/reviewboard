/**
 * Content viewport management.
 *
 * This provides functionality for defining and inspecting a viewport in which
 * page content will be shown, minus any docked page elements.
 *
 * Version Added:
 *     6.0
 */

import { BaseModel, spina } from '@beanbag/spina';


/**
 * Attributes for ContentViewport.
 *
 * Version Added:
 *     6.0
 */
interface ContentViewportAttrs {
    /** The distance from the bottom of the main viewport in pixels. */
    bottom: number;

    /** The distance from the left of the main viewport in pixels. */
    left: number;

    /** The distance from the right of the main viewport in pixels. */
    right: number;

    /** The distance from the top of the main viewport in pixels. */
    top: number;
}


/**
 * A valid viewport side.
 *
 * Version Added:
 *     6.0
 */
export type Side = keyof ContentViewportAttrs;


/**
 * Options for tracking an element.
 *
 * Version Added:
 *     6.0
 */
interface TrackElementOptions {
    /** The element to track. */
    el: Element;

    /** The side the element is docked on. */
    side: Side;
}

/**
 * Tracking data for an element.
 *
 * Version Added:
 *     6.0
 */
interface TrackedElementData {
    /** The last size computed for the element. */
    lastSize: number;

    /** The side the element is docked on. */
    side: Side;
}


/**
 * Management for the viewport in which content is displayed.
 *
 * This provides functionality for defining and inspecting a viewport in which
 * page content will be shown, minus any docked page elements. This can be used
 * to correctly position and align elements related to the content, and to
 * determine where docked elements reside.
 *
 * Docked elements can be tracked, and any size updates will automatically
 * update the viewport.
 *
 * Consumers can listen for the ``change`` signal on the model or on specific
 * sides (e.g., ``change:left``) to determine any updates on the viewport.
 *
 * It's not recommended to set the viewport sizes manually, as they can end up
 * being reset.
 *
 * There is a single instance site-wide, accessible as ``RB.contentViewport``.
 *
 * Version Added:
 *     6.0
 */
@spina
export class ContentViewport extends BaseModel<ContentViewportAttrs> {
    static defaults: ContentViewportAttrs = {
        bottom: 0,
        left: 0,
        right: 0,
        top: 0,
    };

    /**********************
     * Instance variables *
     **********************/

    /**
     * A mapping of docked elements to tracking data.
     */
    #tracked: WeakMap<Element, TrackedElementData> = null;

    /**
     * A stored observer for monitoring resizes.
     */
    #_resizeObserver: ResizeObserver = null;

    /**
     * Clear all tracking state, and reset the viewport.
     */
    clearTracking() {
        const tracked = this.#tracked;

        if (tracked) {
            this.set({
                bottom: 0,
                left: 0,
                right: 0,
                top: 0,
            });

            this.#tracked = null;
        }

        if (this.#_resizeObserver) {
            this.#_resizeObserver.disconnect();
            this.#_resizeObserver = null;
        }
    }

    /**
     * Track a docked element.
     *
     * This will adjust the size of the viewport based on the docked
     * element and its specified side, and will keep it updated whenever
     * the element has resized.
     *
     * Args:
     *     options (TrackElementOptions):
     *         Options used to track the element.
     */
    trackElement(options: TrackElementOptions) {
        let tracked = this.#tracked;
        const el = options.el;
        const side = options.side;

        if (tracked === null) {
            tracked = new WeakMap();
            this.#tracked = tracked;
        } else if (tracked.has(el)) {
            return;
        }

        const size = this.#getElementSize(el, side);

        tracked.set(el, {
            lastSize: size,
            side: side,
        });

        this.attributes[side] += size;

        this.#resizeObserver.observe(el);
    }

    /**
     * Remove a docked element from tracking.
     *
     * This will remove the size of the element from the viewport area and
     * stop tracking it for resizes.
     *
     * Args:
     *     el (Element):
     *         The element to stop tracking.
     */
    untrackElement(el: Element) {
        if (this.#tracked !== null) {
            const data = this.#tracked.get(el);

            if (data !== undefined) {
                this.attributes[data.side] -= data.lastSize;
                this.#tracked.delete(el);
                this.#resizeObserver.unobserve(el);
            }
        }
    }

    /**
     * Return the ResizeObserver for the class.
     *
     * This is constructed and returned the first time it's accessed.
     * Subsequent calls will return the cached copy.
     *
     * Returns:
     *     ResizeObserver:
     *     The resize observer tracking elements.
     */
    get #resizeObserver(): ResizeObserver {
        let observer = this.#_resizeObserver;

        if (observer === null) {
            observer = new ResizeObserver(this.#onObserveResize.bind(this));
            this.#_resizeObserver = observer;
        }

        return observer;
    }

    /**
     * Return the size of an element on a given side.
     *
     * Args:
     *     el (Element):
     *         The element to calculate the size for.
     *
     *     side (Side):
     *         The side to calculate.
     *
     *     rect (DOMRect, optional):
     *         An optional pre-computed bounding rectangle for the element.
     *
     * Returns:
     *     number:
     *     The element size for the given side.
     */
    #getElementSize(
        el: Element,
        side: Side,
        rect?: DOMRect,
    ): number {
        if (rect === undefined) {
            rect = el.getBoundingClientRect();
        }

        return (side === 'top' || side === 'bottom')
               ? rect.height
               : rect.width;
    }

    /**
     * Handle resize events on tracked elements.
     *
     * This will adjust the stored sizes of any sides based on the elements
     * that have resized.
     *
     * Args:
     *     entries (ResizeObserverEntry[]):
     *         The entries that have resized.
     */
    #onObserveResize(entries: ResizeObserverEntry[]) {
        const tracked = this.#tracked;

        if (tracked === null) {
            return;
        }

        const attrs = this.attributes;
        const newValues: Partial<ContentViewportAttrs> = {};

        for (const entry of entries) {
            const el = entry.target;
            const trackedData = tracked.get(el);

            console.assert(trackedData !== undefined);

            const side = trackedData.side;
            const size = this.#getElementSize(el, side, entry.contentRect);

            newValues[side] = (newValues[side] ?? attrs[side]) -
                              trackedData.lastSize + size;
            trackedData.lastSize = size;
        }

        if (newValues) {
            this.set(newValues);
        }

        this.trigger('handledResize');
    }
}


/**
 * A singleton for the main content viewport.
 *
 * This will be available to any callers as ``RB.contentViewport``.
 */
export const contentViewport = new ContentViewport();
