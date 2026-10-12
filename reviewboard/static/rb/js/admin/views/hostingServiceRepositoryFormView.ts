/**
 * Base view for hosting service behavior in the repository form.
 *
 * Version Added:
 *     9.0
 */

import {
    BaseView,
    spina,
} from '@beanbag/spina';

import {
    type RepositoryForm,
    type RepositoryFormHostingAccount,
    type RepositoryFormPlan,
} from '../models/repositoryFormModel';


/**
 * Options for HostingServiceRepositoryFormView.
 *
 * Version Added:
 *     9.0
 */
export interface HostingServiceRepositoryFormViewOptions {
    /**
     * Data for the view, provided by the hosting service.
     *
     * This comes from the hosting service's
     * ``get_repository_form_js_view_data()`` method.
     */
    data: Record<string, unknown>;
}


/**
 * Base view for hosting service behavior in the repository form.
 *
 * The repository form creates one of these when a hosting service is
 * selected, and removes it when another one is selected. The view's
 * element is the whole form, so subclasses can listen to any field.
 *
 * Hosting services can subclass this and set the class name in their
 * ``repository_form_js_view_class`` attribute.
 *
 * Version Added:
 *     9.0
 */
@spina
export class HostingServiceRepositoryFormView extends BaseView<
    RepositoryForm,
    HTMLFormElement,
    HostingServiceRepositoryFormViewOptions
> {
    /**********************
     * Instance variables *
     **********************/

    /** Data for the view, provided by the hosting service. */
    data: Record<string, unknown>;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (HostingServiceRepositoryFormViewOptions):
     *         Options for the view.
     */
    initialize(options: HostingServiceRepositoryFormViewOptions) {
        this.data = options.data;
    }

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
        if (account.hosting_url) {
            return `${account.username} (${account.hosting_url})`;
        } else {
            return account.username;
        }
    }

    /**
     * Return the repository plans to offer for an account.
     *
     * Args:
     *     plans (Array of RepositoryFormPlan):
     *         All the plans for the hosting service.
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
        return plans;
    }

    /**
     * Detach the view from the form.
     *
     * The form is shared with the main repository form view, so only the
     * event handlers are removed. The element is left in place.
     */
    _removeElement() {
        this.undelegateEvents();
    }
}
