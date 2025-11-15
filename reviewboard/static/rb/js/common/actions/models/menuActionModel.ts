import {
    spina,
} from '@beanbag/spina';

import {
    type GroupActionAttrs,
    GroupAction,
} from './groupActionModel';


/**
 * Attributes for the MenuAction model.
 *
 * Version Added:
 *     6.0
 */
export interface MenuActionAttrs extends GroupActionAttrs {}


/**
 * Base model for menu actions.
 *
 * Version Added:
 *     6.0
 */
@spina
export class MenuAction<
    TAttrs extends MenuActionAttrs
> extends GroupAction<TAttrs> {
}
