import {
    type Result,
    spina,
} from '@beanbag/spina';

import {
    type ActionAttrs,
    Action,
} from './actionModel';


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
    static defaults(): Result<Partial<MenuActionAttrs>> {
        return {
            children: [],
        };
    }
}
