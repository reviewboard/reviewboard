import { spina } from '@beanbag/spina';

import { Action, ActionAttrs } from './action';


/**
 * Attributes for the MenuAction model.
 *
 * Version Added:
 *     6.0
 */
interface MenuActionAttrs extends ActionAttrs {
    /**
     * The IDs of the child actions.
     */
    children: string[];
}


/**
 * Base model for menu actions.
 *
 * Version Added:
 *     6.0
 */
@spina
export class MenuAction extends Action<MenuActionAttrs> {
    defaults: MenuActionAttrs = _.extend({
        children: [],
    }, super.defaults);
}
