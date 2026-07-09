/**
 * View for the Connected Services admin page.
 *
 * Version Added:
 *     9.0
 */

import {
    type MenuLabelView,
    craft,
} from '@beanbag/ink';
import {
    BaseView,
    spina,
} from '@beanbag/spina';

import {
    type AccountMenuItem,
    connectedServiceMenuActions,
} from '../connectedServiceMenuActions';
import {
    type ConnectServiceInfo,
    ConnectServiceWizardView,
} from './connectServiceWizardView';


/**
 * Options for ConnectedServicesView.
 *
 * Version Added:
 *     9.0
 */
export interface ConnectedServicesViewOptions {
    /**
     * A connect page to open automatically when the page loads.
     *
     * This is used to finish a connect flow that needs to complete in the
     * wizard (such as returning from a GitHub App installation).
     */
    autoConnectURL?: string | null;

    /**
     * A URL template for the per-service connect endpoint.
     *
     * This contains the placeholder ``__SERVICE_ID__``, which the wizard
     * replaces with the selected service's ID.
     */
    connectURLTemplate: string;

    /** The CSRF token to send with form submissions. */
    csrfToken: string;

    /** The list of services available for connection. */
    services: ConnectServiceInfo[];
}


/**
 * View for the Connected Services admin page.
 *
 * This owns the page's client behavior: opening the connect wizard from the
 * "Connect a service" button and service deep-links, and building the
 * per-account settings menus.
 *
 * Version Added:
 *     9.0
 */
@spina
export class ConnectedServicesView extends BaseView<
    undefined,
    HTMLElement,
    ConnectedServicesViewOptions
> {
    /**********************
     * Instance variables *
     **********************/

    /** The options passed to the view. */
    #options: ConnectedServicesViewOptions;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (ConnectedServicesViewOptions):
     *         The options for the view.
     */
    initialize(options: ConnectedServicesViewOptions) {
        this.#options = options;
    }

    /**
     * Render the view.
     */
    protected onInitialRender() {
        const button = this.el.querySelector('#rb-connect-service-button');

        if (button) {
            button.addEventListener('click', () => this.#openWizard());
        }

        /*
         * Service entries can deep-link to a specific connect step (such as the
         * GitHub App creation page). Open these in the wizard instead of
         * navigating to the bare fragment.
         */
        this.el.addEventListener('click', e => {
            const link = (e.target as HTMLElement)
                .closest('[data-wizard-connect-url]');

            if (link) {
                e.preventDefault();
                this.#openWizard(link.getAttribute('data-wizard-connect-url'));
            }
        });

        this.#buildAccountMenus();
        this.#wireAttentionAlert();

        if (this.#options.autoConnectURL) {
            /*
             * A connect flow asked us to finish in the wizard. The URL is built
             * by the server, not taken from a query parameter, so it is safe to
             * load.
             */
            this.#openWizard(this.#options.autoConnectURL);
        }
    }

    /**
     * Open the connect wizard.
     *
     * Args:
     *     initialConnectURL (string, optional):
     *         A connect page to open directly, skipping the service picker.
     */
    #openWizard(initialConnectURL?: string) {
        const wizard = new ConnectServiceWizardView({
            connectURLTemplate: this.#options.connectURLTemplate,
            csrfToken: this.#options.csrfToken,
            initialConnectURL: initialConnectURL ?? undefined,
            services: this.#options.services,
        });

        wizard.render();
        wizard.open();
    }

    /**
     * Build the settings menu for each account row.
     */
    #buildAccountMenus() {
        for (const el of this.el.querySelectorAll<HTMLElement>(
                 '[data-account-menu]')) {
            const dataEl = el.querySelector('script[type="application/json"]');

            if (!dataEl) {
                continue;
            }

            let items: AccountMenuItem[];

            try {
                items = JSON.parse(dataEl.textContent);
            } catch {
                continue;
            }

            if (!items.length) {
                continue;
            }

            const accountID = el.dataset.accountId;
            const serviceID = el.dataset.serviceId;

            const menuLabelView = craft<MenuLabelView>`
                <Ink.MenuLabel dropDownIconName=${null}
                               iconName="ink-i-settings"
                               menuAriaLabel="${_`Account actions`}">
                 ${items.map(item => craft`
                  <Ink.MenuLabel.Item
                    iconName=${item.iconName ?? null}
                    onClick=${() => this.#onMenuItem(
                        item, accountID, serviceID)}>
                   ${item.label}
                  </Ink.MenuLabel.Item>
                 `)}
                </Ink.MenuLabel>
            `;

            menuLabelView.renderInto(el);
        }
    }

    /**
     * Wire up the fix actions in the "needs attention" alert.
     *
     * Each fix control carries the same descriptor as an account menu item, so
     * clicking it dispatches through the same handler. This resolves the
     * problem the same way the account's own menu would: opening a dialog,
     * navigating to a URL, or running a registered handler.
     */
    #wireAttentionAlert() {
        const fixEls = this.el.querySelectorAll<HTMLElement>('[data-attention-fix]')

        for (const el of fixEls) {
            const dataEl = el.querySelector('script[type="application/json"]');
            const button = el.querySelector('button');

            if (!dataEl || !button) {
                continue;
            }

            let item: AccountMenuItem;

            try {
                item = JSON.parse(dataEl.textContent);
            } catch {
                continue;
            }

            const accountID = el.dataset.accountId;
            const serviceID = el.dataset.serviceId;

            button.addEventListener('click', () => this.#onMenuItem(
                item, accountID, serviceID));
        }
    }

    /**
     * Handle a click on an account menu item.
     *
     * The item's action is determined by which field is set: ``dialogURL``
     * opens the item in the connect wizard, ``url`` navigates to the URL, and
     * ``action`` runs a handler registered in the client action registry.
     *
     * Args:
     *     item (AccountMenuItem):
     *         The menu item that was clicked.
     *
     *     accountID (string):
     *         The ID of the account the menu is for.
     *
     *     serviceID (string):
     *         The ID of the hosting service the account belongs to.
     */
    #onMenuItem(
        item: AccountMenuItem,
        accountID: string,
        serviceID: string,
    ) {
        if (item.dialogURL) {
            this.#openWizard(item.dialogURL);
        } else if (item.url) {
            window.location.href = item.url;
        } else if (item.action) {
            connectedServiceMenuActions.get(item.action)?.({
                accountID,
                item,
                serviceID,
            });
        }
    }
}
