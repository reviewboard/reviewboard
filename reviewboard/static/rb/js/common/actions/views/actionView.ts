import { BaseView, spina } from '@beanbag/spina';

import { type Action } from '../models/actionModel';


/**
 * Base view for actions.
 *
 * Version Added:
 *     6.0
 */
@spina
export class ActionView<
    TModel extends Action = Action,
    TElement extends HTMLDivElement = HTMLDivElement,
    TExtraViewOptions extends object = object
> extends BaseView<TModel, TElement, TExtraViewOptions> {
    /**********************
     * Instance variables *
     **********************/

    /**
     * The element used to manage the action's visibility.
     *
     * Version Added:
     *     7.1
     */
    #visibilityEl: HTMLElement = null;

    /**
     * Return whether this action is visible.
     *
     * This will return the visibility status of the action parent container
     * (if available) or of this view's element (if contained in another
     * parent).
     *
     * Version Added:
     *     7.1
     *
     * Returns:
     *     boolean:
     *     ``true`` if the action is visible. ``false`` if it is not.
     */
    isVisible(): boolean {
        const el = this.#getVisibilityEl();

        return !el.hidden && el.style.display !== 'none';
    }

    /**
     * Show the action.
     *
     * This will show the action parent container (if available) or this
     * view's element (if contained in another parent).
     *
     * Version Added:
     *     7.1
     *
     * Returns:
     *     ActionView:
     *     This view, for chaining.
     */
    show(): this {
        const visibilityEl = this.#getVisibilityEl();

        $(visibilityEl).show();
        visibilityEl.hidden = false;

        return this;
    }

    /**
     * Hide the action.
     *
     * This will hide the action parent container (if available) or this
     * view's element (if contained in another parent).
     *
     * Version Added:
     *     7.1
     *
     * Returns:
     *     ActionView:
     *     This view, for chaining.
     */
    hide(): this {
        const visibilityEl = this.#getVisibilityEl();

        $(visibilityEl).hide();
        visibilityEl.hidden = true;

        return this;
    }

    /**
     * Return the element responsible for the action's visibility.
     *
     * If the view is inside an action parent container (one using the
     * ``rb-c-actions__action`` CSS class), that elment will be returned.
     * If the view is inside another parent, then this view's element
     * will be returned.
     *
     * The result is cached for future use.
     *
     * Version Added:
     *     7.1
     *
     * Returns:
     *     HTMLElement:
     *     The element responsible for visibility.
     */
    #getVisibilityEl(): HTMLElement {
        let visibilityEl = this.#visibilityEl;

        if (visibilityEl === null) {
            const el = this.el;
            const parentEl = el.parentElement;

            visibilityEl = (
                parentEl.classList.contains('rb-c-actions__action')
                ? parentEl
                : el);

            this.#visibilityEl = visibilityEl;
        }

        return visibilityEl;
    }
}
