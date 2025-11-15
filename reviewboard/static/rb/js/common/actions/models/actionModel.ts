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
     * Whether this is a Quick Access action.
     *
     * Version Added:
     *     7.1
     */
    isQuickAccess: boolean;

    /**
     * Whether this Quick Access action is enabled.
     *
     * Version Added:
     *     7.1
     */
    isQuickAccessEnabled: boolean;

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
     * The verbose label for the action.
     *
     * This can be used to provide a longer label for wider UIs that would
     * benefit from a more descriptive label. It's also intended for ARIA
     * labels.
     *
     * It's always optional.
     *
     * Version Added:
     *     7.1
     */
    verboseLabel: string | null;

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
 * Version Changed:
 *     7.1:
 *     This is now the preferred place to put any action activation code.
 *     Multiple views could wrap a single action.
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
        isQuickAccess: false,
        isQuickAccessEnabled: false,
        label: null,
        url: null,
        verboseLabel: null,
        visible: false,
    };

    /**
     * Activate the action.
     *
     * This can be invoked by action views to enable default behaviors.
     *
     * By default, this does nothing.
     *
     * Version Added:
     *     7.1
     */
    activate() {
        // This can be overridden by subclasses for actions.
    }
}
