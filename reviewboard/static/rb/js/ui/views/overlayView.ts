/**
 * An overlay to capture events.
 *
 * Version Added:
 *     6.0
 */

import { BaseView, spina } from '@beanbag/spina';

/**
 * An overlay to capture events.
 *
 * Version Added:
 *     6.0
 */
@spina
export class OverlayView extends BaseView {
    static className = 'rb-c-event-overlay';
    static events = {
        'click': '_onClick',
        'touchstart': '_onClick',
    };

    /**
     * Handle a click or other interaction.
     *
     * This will trigger an event which can be handled by the owner.
     */
    private _onClick(e: MouseEvent | TouchEvent) {
        e.stopPropagation();
        e.preventDefault();

        this.trigger('click');
    }
}
