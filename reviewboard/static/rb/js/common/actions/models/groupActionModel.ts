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
     * The IDs of the child actions, grouped by attachment point ID.
     *
     * Version Changed:
     *     7.1:
     *     This is now organized by attachment point ID.
     */
    children: Record<string, string[]>;
}


/**
 * Base model for group actions.
 *
 * Version Added:
 *     6.0
 */
@spina
export class GroupAction<
    TAttrs extends GroupActionAttrs
> extends Action<TAttrs> {
    /**
     * Return default attributes for the action.
     *
     * Returns:
     *     GroupActionAttrs:
     *     The default attributes.
     */
    static defaults(): Partial<GroupActionAttrs> {
        return {
            children: {},
        };
    }
}
