import { BaseView, spina } from '@beanbag/spina';

import { type Action } from '../models/actionModel';


/**
 * Options passed to an ActionView.
 *
 * Version Added:
 *     7.1
 */
export interface ActionViewOptions {
    /**
     * The action attachment point for this view.
     *
     * Version Added:
     *     7.1
     */
    attachmentPointID: string;
}


/**
 * Base view for actions.
 *
 * Version Added:
 *     6.0
 */
@spina
export class ActionView<
    TModel extends Action = Action,
    TElement extends HTMLElement = HTMLDivElement,
    TOptions extends ActionViewOptions = ActionViewOptions
> extends BaseView<TModel, TElement, TOptions> {
    static modelEvents = {
        'change:visible': '_onVisibleChanged',
    };

    /**********************
     * Instance variables *
     **********************/

    /**
     * The action attachment point for this view.
     *
     * Version Added:
     *     7.1
     */
    attachmentPointID: string;

    /**
     * Whether this action view is locally visible.
     *
     * This controls whether this action view is visible, separately from
     * the action model's ``visible`` state. The action will be visible only
     * if locally visible and if the action has ``visible=true``.
     *
     * Version Added:
     *     7.1
     */
    #locallyVisible = true;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (AttachmentViewOptions):
     *         The options passed to the view.
     */
    initialize(
        options: TOptions,
    ) {
        this.attachmentPointID = options.attachmentPointID;
    }

    /**
     * The element used to manage the action's visibility.
     *
     * Version Added:
     *     7.1
     */
    #visibilityEl: HTMLElement = null;

    /**
     * Show the action.
     *
     * This will show the action parent container (if available) or this
     * view's element (if contained in another parent) when the action's
     * ``visible`` attribute is ``true``.
     *
     * Version Added:
     *     7.1
     *
     * Returns:
     *     ActionView:
     *     This view, for chaining.
     */
    show(): this {
        this.#locallyVisible = true;
        this._onVisibleChanged();

        return this;
    }

    /**
     * Hide the action.
     *
     * This will hide the action parent container (if available) or this
     * view's element (if contained in another parent) regardless of the
     * action's ``visible`` attribute.
     *
     * Version Added:
     *     7.1
     *
     * Returns:
     *     ActionView:
     *     This view, for chaining.
     */
    hide(): this {
        this.#locallyVisible = false;
        this._onVisibleChanged();

        return this;
    }

    /**
     * Activate the action.
     *
     * By default, this invokes the ``activate`` method on the action model.
     * This can be overridden to perform different logic.
     *
     * Version Added:
     *     7.1
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the activation.
     */
    async activate() {
        await this.model.activate();
    }

    /**
     * Handle the initial render of the view.
     *
     * Version Added:
     *     7.1
     */
    protected onInitialRender() {
        this._onVisibleChanged();
    }

    /**
     * Handle changes to the action's visibility.
     *
     * This will update the visibility of the action's view to match the
     * visibility state, handling both appearance and accessibility.
     *
     * Version Added:
     *     7.1
     */
    private _onVisibleChanged() {
        const visibilityEl = this.#getVisibilityEl();
        const visible = this.#locallyVisible && this.model.get('visible');

        /*
         * The visibility state has changed. Show/hide and update the
         * hidden attribute.
         */
        if (visible) {
            $(visibilityEl).show();
            visibilityEl.hidden = false;
        } else {
            $(visibilityEl).hide();
            visibilityEl.hidden = true;
        }
    }

    /**
     * Return the element responsible for the action's visibility.
     *
     * If the view is inside an action parent container (one using the
     * ``rb-c-actions__action`` CSS class), that element will be returned.
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
