import {
    type Result,
    BaseModel,
    spina,
} from '@beanbag/spina';


/**
 * Attributes for the Action model.
 *
 * Version Changed:
 *     7.0:
 *     Added ``domID``, ``iconClass``, ``isCustomRendered``, ``label``, and
 *     ``url`` actions.
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
     * The explicit ID to use for a DOM element.
     *
     * Version Added:
     *     7.0
     */
    domID: string | null;

    /**
     * The icon class name for the action.
     *
     * Version Added:
     *     7.0
     */
    iconClass: string | null;

    /**
     * Whether the action uses custom rendering.
     *
     * This may impact the native rendering of the action and should be
     * used carefully.
     *
     * Version Added:
     *     7.0
     */
    isCustomRendered: boolean;

    /**
     * The label for the action.
     *
     * Version Added:
     *     7.0
     */
    label: string | null;

    /**
     * An optional URL to navigate to when the action is invoked.
     *
     * Version Added:
     *     7.0
     */
    url: string | null;

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
export class Action<
    TAttrs extends ActionAttrs = ActionAttrs,
> extends BaseModel<TAttrs> {
    static defaults: Result<Partial<ActionAttrs>> = {
        actionId: '',
        domID: null,
        iconClass: null,
        isCustomRendered: false,
        label: null,
        url: null,
        visible: false,
    };
}
