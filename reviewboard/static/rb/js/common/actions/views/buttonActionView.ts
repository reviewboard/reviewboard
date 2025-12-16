/**
 * Action view for a button.
 *
 * Version Added:
 *     7.1
 */

import { spina } from '@beanbag/spina';

import { type Action } from '../models/actionModel';
import { ActionView } from './actionView';


/**
 * Action view for a button.
 *
 * This renders a standard Ink button, activating the action on click and
 * using the button's busy state to indicate the action is being performed.
 *
 * Version Added:
 *     7.1
 */
@spina
export class ButtonActionView<
    TModel extends Action = Action,
    TElement extends HTMLElement = HTMLButtonElement,
    TExtraViewOptions extends object = object,
> extends ActionView<TModel, TElement, TExtraViewOptions> {
    static events = {
        'click': '_onClick',
    };

    /**
     * Handle a click event.
     *
     * This will mark the button as busy, activate the action, and then
     * remove the busy state once the activation concludes.
     *
     * Args:
     *     e (MouseEvent):
     *         The click event.
     */
    private async _onClick(
        e: MouseEvent,
    ) {
        e.stopPropagation();
        e.preventDefault();

        const el = this.el;

        el.setAttribute('aria-busy', 'true');

        try {
            await this.model.activate();
        } finally {
            el.removeAttribute('aria-busy');
        }
    }
}
