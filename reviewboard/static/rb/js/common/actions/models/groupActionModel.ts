import {
    type Result,
    spina,
} from '@beanbag/spina';

import {
    type ActionAttrs,
    Action,
} from './actionModel';


/**
 * Attributes for the GroupAction model.
 *
 * Version Added:
 *     6.0
 */
export interface GroupActionAttrs extends ActionAttrs {
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
export class GroupAction<
    TAttrs extends GroupActionAttrs
> extends Action<TAttrs> {
    static defaults(): Result<Partial<GroupActionAttrs>> {
        return {
            children: [],
        };
    }
}
