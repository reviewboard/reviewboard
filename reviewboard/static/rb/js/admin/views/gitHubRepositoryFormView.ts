/**
 * GitHub behavior for the repository form.
 *
 * Version Added:
 *     9.0
 */

import { spina } from '@beanbag/spina';

import {
    type RepositoryFormHostingAccount,
    type RepositoryFormPlan,
} from '../models/repositoryFormModel';
import {
    HostingServiceRepositoryFormView,
} from './hostingServiceRepositoryFormView';


/**
 * GitHub behavior for the repository form.
 *
 * GitHub App installations are bound to a single user or organization, so
 * they only use the ``app`` plan. Other accounts, and new accounts being
 * linked, use the remaining plans.
 *
 * Accounts are labeled so that installations and Personal Access Token
 * accounts with the same name can be told apart.
 *
 * Version Added:
 *     9.0
 */
@spina
export class GitHubRepositoryFormView extends HostingServiceRepositoryFormView {
    /**
     * Return the label for an account in the Hosting Account field.
     *
     * Args:
     *     account (RepositoryFormHostingAccount):
     *         The account to label.
     *
     * Returns:
     *     string:
     *     The label for the account.
     */
    getAccountLabel(
        account: RepositoryFormHostingAccount,
    ): string {
        const labels = this.data.accountLabels as Record<string, string>;

        return labels[account.pk] ?? super.getAccountLabel(account);
    }

    /**
     * Return the repository plans to offer for an account.
     *
     * Args:
     *     plans (Array of RepositoryFormPlan):
     *         All the plans for GitHub.
     *
     *     account (RepositoryFormHostingAccount):
     *         The selected account, or ``null`` when linking a new account.
     *
     * Returns:
     *     Array of RepositoryFormPlan:
     *     The plans to offer.
     */
    getRepositoryPlans(
        plans: RepositoryFormPlan[],
        account: RepositoryFormHostingAccount | null,
    ): RepositoryFormPlan[] {
        const appAccountIDs = this.data.appAccountIDs as number[];
        const isApp = (account !== null &&
                       appAccountIDs.includes(account.pk));

        return plans.filter(plan => (plan.id === 'app') === isApp);
    }
}
