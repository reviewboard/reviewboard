/**
 * Registry of client-side handlers for account menu items.
 *
 * Version Added:
 *     9.0
 */


/**
 * A descriptor for an item in an account's settings menu.
 *
 * This mirrors the server-side descriptor built by
 * ``BaseHostingService.get_admin_services_list_account_menu_items``. The action
 * an item performs on click is determined by which of the action fields is set.
 *
 * Version Added:
 *     9.0
 */
export interface AccountMenuItem {
    /** A unique identifier for the item within the menu. */
    id: string;

    /** The label to show for the item. */
    label: string;

    /** The name of an optional icon to show beside the label. */
    iconName?: string;

    /** A connect-page URL to open in the services dialog when clicked. */
    dialogURL?: string;

    /** A URL to navigate to when the item is clicked. */
    url?: string;

    /** The name of a registered client-side handler to run when clicked. */
    action?: string;
}


/**
 * Context passed to an account menu action handler.
 *
 * Version Added:
 *     9.0
 */
export interface AccountMenuActionContext {
    /** The ID of the account the menu is for. */
    accountID: string;

    /** The ID of the hosting service the account belongs to. */
    serviceID: string;

    /** The menu item that was clicked. */
    item: AccountMenuItem;
}


/**
 * A handler for a custom account menu action.
 *
 * Version Added:
 *     9.0
 */
export type AccountMenuActionHandler = (
    context: AccountMenuActionContext,
) => void;


/**
 * A registry of named handlers for custom account menu items.
 *
 * Hosting services and extensions register handlers here for menu items that
 * use the ``action`` field. Handlers are looked up at click time, so
 * registration order relative to the menu build does not matter.
 *
 * Version Added:
 *     9.0
 */
class ConnectedServiceMenuActionRegistry {
    /** The registered handlers, keyed by name. */
    #handlers = new Map<string, AccountMenuActionHandler>();

    /**
     * Register a handler for a named action.
     *
     * Args:
     *     name (string):
     *         The action name, matching a menu item's ``action`` field.
     *
     *     handler (AccountMenuActionHandler):
     *         The handler to run when an item with that action is clicked.
     */
    register(
        name: string,
        handler: AccountMenuActionHandler,
    ) {
        this.#handlers.set(name, handler);
    }

    /**
     * Return the handler registered for a named action.
     *
     * Args:
     *     name (string):
     *         The action name to look up.
     *
     * Returns:
     *     AccountMenuActionHandler:
     *     The registered handler, or ``undefined`` if none is registered.
     */
    get(
        name: string,
    ): AccountMenuActionHandler | undefined {
        return this.#handlers.get(name);
    }
}


/**
 * The shared registry of account menu action handlers.
 *
 * Version Added:
 *     9.0
 */
export const connectedServiceMenuActions =
    new ConnectedServiceMenuActionRegistry();
