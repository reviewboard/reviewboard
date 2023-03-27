import { BaseModel, spina } from '@beanbag/spina';


/**
 * Attributes for the Action model.
 *
 * Version Added:
 *     6.0
 */
export interface ActionAttrs {
    /**
     * The ID of the action.
     */
    actionId: string;

    /**
     * Whether the action should be visible or hidden.
     */
    visible: boolean;
}


/**
 * Base model for actions.
 *
 * Subclasses may add their own attributes by passing in their own attribute
 * interface when extending this.
 *
 * Version Added:
 *     6.0
 */
@spina
export class Action<T = ActionAttrs> extends BaseModel<T> {
    static defaults: Partial<ActionAttrs> = {
        actionId: '',
        visible: false,
    };
}
