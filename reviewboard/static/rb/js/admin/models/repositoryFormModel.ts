/**
 * Model for the repository configuration form.
 *
 * Version Added:
 *     9.0
 */

import {
    BaseModel,
    spina,
} from '@beanbag/spina';


/**
 * A linked hosting service account offered by the repository form.
 *
 * Version Added:
 *     9.0
 */
export interface RepositoryFormHostingAccount {
    /** The account's hosting URL, for self-hosted services. */
    hosting_url: string | null;

    /** Whether the account is currently authorized. */
    is_authorized: boolean;

    /** The account's ID. */
    pk: number;

    /** The account's username. */
    username: string;
}


/**
 * A repository plan offered by a hosting service.
 *
 * Version Added:
 *     9.0
 */
export interface RepositoryFormPlan {
    /** The plan's ID. */
    id: string;

    /** The plan's display label. */
    label: string;
}


/**
 * Information on a hosting service, provided by the server.
 *
 * Version Added:
 *     9.0
 */
export interface RepositoryFormHostingServiceInfo {
    /** The linked accounts for the service. */
    accounts: RepositoryFormHostingAccount[];

    /** Whether the user needs to enter a two-factor auth code. */
    needs_two_factor_auth_code: boolean;

    /** The repository plans offered by the service. */
    plans: RepositoryFormPlan[];

    /** The IDs or names of the SCMTools the service supports. */
    scmtools: string[];

    /** Whether the service supports associating SSH keys. */
    supports_ssh_key_association: boolean;

    /** Whether this is a placeholder for a service that isn't installed. */
    fake?: boolean;
}


/**
 * Information on an SCMTool, provided by the server.
 *
 * Version Added:
 *     9.0
 */
export interface RepositoryFormSCMToolInfo {
    /** The tool's display name. */
    name: string;

    /** Whether this is a placeholder for a tool that isn't installed. */
    fake?: boolean;
}


/**
 * Attributes for the RepositoryForm model.
 *
 * Version Added:
 *     9.0
 */
export interface RepositoryFormAttrs {
    /** The selected hosting account ID, or ``null`` to link a new one. */
    hostingAccountID: number | null;

    /** Information on each hosting service, keyed by ID. */
    hostingServices: Record<string, RepositoryFormHostingServiceInfo>;

    /** The selected hosting service ID, or ``custom``. */
    hostingType: string;

    /** The selected repository plan ID, if any. */
    repositoryPlan: string | null;

    /** The selected SCMTool ID. */
    tool: string;

    /** Information on each SCMTool, keyed by ID. */
    tools: Record<string, RepositoryFormSCMToolInfo>;
}


/**
 * State for the repository configuration form.
 *
 * This tracks the form's main selections, along with the server-provided
 * information on hosting services and SCMTools.
 *
 * Version Added:
 *     9.0
 */
@spina
export class RepositoryForm extends BaseModel<RepositoryFormAttrs> {
    static defaults: RepositoryFormAttrs = {
        hostingAccountID: null,
        hostingServices: {},
        hostingType: 'custom',
        repositoryPlan: null,
        tool: '',
        tools: {},
    };

    /**
     * Return whether a hosting service is selected.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the repository is configured with a hosting service.
     *     ``false``, otherwise.
     */
    isHostingServiceSelected(): boolean {
        return this.get('hostingType') !== 'custom';
    }

    /**
     * Return information on the selected hosting service.
     *
     * Returns:
     *     RepositoryFormHostingServiceInfo:
     *     The service information, or ``null`` if no hosting service is
     *     selected.
     */
    getHostingServiceInfo(): RepositoryFormHostingServiceInfo | null {
        if (!this.isHostingServiceSelected()) {
            return null;
        }

        return this.get('hostingServices')[this.get('hostingType')] ?? null;
    }

    /**
     * Return whether the selected hosting service isn't installed.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the selected hosting service is a placeholder.
     */
    isFakeHostingService(): boolean {
        return this.getHostingServiceInfo()?.fake === true;
    }

    /**
     * Return the selected hosting account.
     *
     * Returns:
     *     RepositoryFormHostingAccount:
     *     The account, or ``null`` if linking a new account.
     */
    getSelectedAccount(): RepositoryFormHostingAccount | null {
        const accountID = this.get('hostingAccountID');
        const info = this.getHostingServiceInfo();

        if (accountID === null || info === null) {
            return null;
        }

        return info.accounts.find(account => (account.pk === accountID)) ??
               null;
    }
}
