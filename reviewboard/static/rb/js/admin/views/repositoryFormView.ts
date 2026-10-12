/**
 * View for the repository configuration form.
 *
 * Version Added:
 *     9.0
 */

import { paint } from '@beanbag/ink';
import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';
import { dedent } from 'babel-plugin-dedent';

import { type RepositoryForm } from '../models/repositoryFormModel';
import {
    HostingServiceRepositoryFormView,
} from './hostingServiceRepositoryFormView';
import { SCMToolRepositoryFormView } from './scmToolRepositoryFormView';


/**
 * Options for RepositoryFormView.
 *
 * Version Added:
 *     9.0
 */
export interface RepositoryFormViewOptions {
    /**
     * The view class for each hosting service, keyed by ID.
     *
     * Services that aren't listed use
     * :js:class:`HostingServiceRepositoryFormView`.
     */
    hostingServiceViews?: Record<string,
                                 typeof HostingServiceRepositoryFormView>;

    /**
     * The view class for each SCMTool, keyed by ID.
     *
     * SCMTools that aren't listed use
     * :js:class:`SCMToolRepositoryFormView`.
     */
    scmToolViews?: Record<string, typeof SCMToolRepositoryFormView>;
}


/**
 * Type for an SCMTool option that the form is rendered with.
 *
 * Version Added:
 *     9.0
 */
interface RepositoryFormToolOption {
    /** The user-visible text for the option. */
    text: string;

    /** The value for the option. */
    value: string;
}


/**
 * View for the repository configuration form.
 *
 * This keeps the model in sync with the form's main fields, and shows the
 * fields, sub-forms and notices that apply to the selected hosting
 * service, account, plan and SCMTool.
 *
 * Hosting services and SCMTools can change how the form behaves through
 * their own views. See :js:class:`HostingServiceRepositoryFormView` and
 * :js:class:`SCMToolRepositoryFormView`.
 *
 * Version Added:
 *     9.0
 */
@spina
export class RepositoryFormView extends BaseView<
    RepositoryForm,
    HTMLFormElement,
    RepositoryFormViewOptions
> {
    static events: EventsHash = {
        'change #id_hosting_account': '_onHostingAccountChanged',
        'change #id_hosting_type': '_onHostingTypeChanged',
        'change #id_public': '_updatePublicAccess',
        'change #id_repository_plan': '_onRepositoryPlanChanged',
        'change #id_tool': '_onToolChanged',
        'click #repo-edit-hosting-credentials': '_onEditCredentialsClicked',
    };

    static modelEvents: EventsHash = {
        'change:hostingAccountID': '_onModelHostingAccountChanged',
        'change:hostingType': '_onModelHostingTypeChanged',
        'change:repositoryPlan': '_updateHostingRepoForms',
        'change:tool': '_updateSCMToolForms',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The SSH key association checkbox. */
    #$associateSSHKey: JQuery;

    /** The fieldset containing the SSH key association checkbox. */
    #$associateSSHKeyFieldset: JQuery;

    /** The link for editing the hosting account's credentials. */
    #$editCredentials: JQuery;

    /** The label of the link for editing credentials. */
    #$editCredentialsLabel: JQuery;

    /** The hidden field for forcing re-authorization. */
    #$forceAuth: JQuery;

    /** The notice shown when Gerrit is selected. */
    #$gerritPluginInfo: JQuery;

    /** The Hosting Account field. */
    #$hostingAccount: JQuery;

    /** The notice shown when an account needs to be re-linked. */
    #$hostingAccountRelink: JQuery;

    /** The Hosting Account row. */
    #$hostingAccountRow: JQuery;

    /** All hosting service authentication sub-forms. */
    #$hostingAuthForms: JQuery;

    /** The Power Pack advert for hosting services. */
    #$hostingPowerPackAdvert: JQuery;

    /** All hosting service repository sub-forms. */
    #$hostingRepoForms: JQuery;

    /** The Hosting Type field. */
    #$hostingType: JQuery;

    /** The Repository Plan field. */
    #$repoPlan: JQuery;

    /** The Repository Plan row. */
    #$repoPlanRow: JQuery;

    /** All SCMTool authentication sub-forms. */
    #$scmtoolAuthForms: JQuery;

    /** All SCMTool repository sub-forms. */
    #$scmtoolRepoForms: JQuery;

    /** The form's submit buttons. */
    #$submitButtons: JQuery;

    /** The Repository Type field. */
    #$tool: JQuery;

    /** The Power Pack advert for SCMTools. */
    #$toolPowerPackAdvert: JQuery;

    /** The Repository Type row. */
    #$toolRow: JQuery;

    /** The view for the selected hosting service. */
    #hostingServiceView: (HostingServiceRepositoryFormView | null) = null;

    /** The view class for each hosting service, keyed by ID. */
    #hostingServiceViews: Record<string,
                                 typeof HostingServiceRepositoryFormView>;

    /** The view for the selected SCMTool. */
    #scmToolView: (SCMToolRepositoryFormView | null) = null;

    /** The view class for each SCMTool, keyed by ID. */
    #scmToolViews: Record<string, typeof SCMToolRepositoryFormView>;

    /** Whether SSH key association was disabled when the page loaded. */
    #associateSSHKeyDisabled: boolean;

    /** Every SCMTool option the form was rendered with. */
    #toolOptions: Array<RepositoryFormToolOption>;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (RepositoryFormViewOptions):
     *         Options for the view.
     */
    initialize(options: RepositoryFormViewOptions = {}) {
        this.#hostingServiceViews = options.hostingServiceViews ?? {};
        this.#scmToolViews = options.scmToolViews ?? {};
    }

    /**
     * Render the view.
     */
    protected onInitialRender() {
        this.#$hostingType = this.$('#id_hosting_type');
        this.#$hostingAccount = this.$('#id_hosting_account');
        this.#$hostingAccountRow = this.$('#row-hosting_account');
        this.#$hostingAuthForms = this.$('.hosting-auth-form');
        this.#$hostingRepoForms = this.$('.hosting-repo-form');
        this.#$scmtoolAuthForms = this.$('.scmtool-auth-form');
        this.#$scmtoolRepoForms = this.$('.scmtool-repo-form');
        this.#$associateSSHKey = this.$('#id_associate_ssh_key');
        this.#$associateSSHKeyFieldset =
            this.$('#row-associate_ssh_key').closest('fieldset');
        this.#associateSSHKeyDisabled =
            this.#$associateSSHKey.prop('disabled');
        this.#$repoPlan = this.$('#id_repository_plan');
        this.#$repoPlanRow = this.$('#row-repository_plan');
        this.#$tool = this.$('#id_tool');
        this.#$toolRow = this.$('#row-tool');
        this.#$submitButtons = this.$('input[type="submit"]');
        this.#$editCredentials = this.$('#repo-edit-hosting-credentials');
        this.#$editCredentialsLabel =
            this.$('#repo-edit-hosting-credentials-label');
        this.#$forceAuth = this.$('#id_force_authorize');

        this.#$hostingAccountRelink = $(paint<HTMLParagraphElement>`
            <p class="errornote">
             ${_`The authentication requirements for this account have changed.
             You will need to re-authenticate.`}
            </p>
        `)
            .hide()
            .appendTo(this.#$hostingAccountRow);

        const ppRequiredText = _`Power Pack Required`;
        const ppRequiredDetailHTML = _`
            <span class="power-pack-advert-hosting-type"></span>
            support is available with
            <a href="https://www.reviewboard.org/powerpack/">Power Pack</a>, an
            extension which also offers powerful reports, PDF and Office
            document review, and more.
        `;

        this.#$hostingPowerPackAdvert = $(paint<HTMLDivElement>`
            <div class="powerpack-advert">
             <h3>${ppRequiredText}</h3>
             <p>${paint([ppRequiredDetailHTML])}</p>
            </div>
        `)
            .hide()
            .appendTo(this.#$hostingType.closest('fieldset'));

        this.#$toolPowerPackAdvert = $(paint<HTMLDivElement>`
            <div class="powerpack-advert">
             <h3>${ppRequiredText}</h3>
             <p>${paint([ppRequiredDetailHTML])}</p>
            </div>
        `)
            .hide()
            .appendTo(this.#$tool.closest('fieldset'));

        const gerritManualURL =
            MANUAL_URL + 'admin/configuration/repositories/gerrit/';
        const gerritRequiredDetailHTML = _`
            The <code>gerrit-reviewboard</code> plugin is required for Gerrit
            integration. See the
            <a href="${gerritManualURL}" target="_blank">instructions</a> for
            installing the plugin on your server.
        `;
        this.#$gerritPluginInfo = $(paint<HTMLDivElement>`
            <div class="gerrit-plugin-advert">
             <h3>${_`Plugin Required`}</h3>
             <p>${paint([gerritRequiredDetailHTML])}</p>
            </div>
        `)
            .hide()
            .appendTo(this.$('#row-hosting_type'));

        this.#toolOptions = this.#$tool.children().toArray().map(el => ({
            text: el.textContent,
            value: (el as HTMLOptionElement).value,
        }));

        /*
         * The hosting service SSH public key link lives outside the form,
         * in the page's alerts.
         */
        const $showSSHKey = $('#show-ssh-key-link');
        const $publicKeyPopup = $('#ssh-public-key-popup');

        $showSSHKey.on('click', () => {
            if ($publicKeyPopup.is(':visible')) {
                $showSSHKey.text(_`Show your SSH public key`);
                $publicKeyPopup.hide();
            } else {
                $showSSHKey.text(_`Hide your SSH public key`);
                $publicKeyPopup.show();
            }

            return false;
        });

        this.model.set({
            hostingAccountID: this.#getAccountFieldValue(),
            hostingType: this.#$hostingType.val() as string,
            repositoryPlan: (this.#$repoPlan.val() as string) || null,
            tool: this.#$tool.val() as string,
        }, {
            silent: true,
        });

        this._onModelHostingTypeChanged();
        this._updatePublicAccess();
    }

    /**
     * Remove the view.
     */
    protected onRemove() {
        this.#hostingServiceView?.remove();
        this.#scmToolView?.remove();
    }

    /**
     * Return the hosting account ID selected in the form.
     *
     * Returns:
     *     number:
     *     The selected account ID, or ``null`` to link a new account.
     */
    #getAccountFieldValue(): number | null {
        const value = this.#$hostingAccount.val() as string;

        if (value) {
            return parseInt(value, 10);
        } else {
            return null;
        }
    }

    /**
     * Handle a change to the Hosting Type field.
     *
     * This will set the new value into the model.
     */
    private _onHostingTypeChanged() {
        this.model.set('hostingType', this.#$hostingType.val() as string);
    }

    /**
     * Handle a change to the Hosting Account field.
     *
     * This will set the new value into the model.
     */
    private _onHostingAccountChanged() {
        this.model.set('hostingAccountID', this.#getAccountFieldValue());
    }

    /**
     * Handle a change to the Repository Plan field.
     *
     * This will set the new value into the model.
     */
    private _onRepositoryPlanChanged() {
        this.model.set('repositoryPlan',
                       (this.#$repoPlan.val() as string) || null);
    }

    /**
     * Handle a change to the Repository Type field.
     *
     * This will set the new value into the model.
     */
    private _onToolChanged() {
        this.model.set('tool', this.#$tool.val() as string);
    }

    /**
     * Update the form for a newly-selected hosting service.
     *
     * This rebuilds the lists of SCMTools, accounts and plans for the
     * service, and shows the rows and notices that apply to it.
     */
    private _onModelHostingTypeChanged() {
        const model = this.model;
        const onHostingService = model.isHostingServiceSelected();
        const isFake = model.isFakeHostingService();
        const info = model.getHostingServiceInfo();

        this.#$gerritPluginInfo.toggle(model.get('hostingType') === 'gerrit');

        if (info !== null && info.supports_ssh_key_association) {
            /* Use the state of the checkbox from when the page loaded. */
            this.#$associateSSHKey.prop('disabled',
                                        this.#associateSSHKeyDisabled);
            this.#$associateSSHKeyFieldset.show();
        } else {
            this.#$associateSSHKeyFieldset.hide();
            this.#$associateSSHKey.prop({
                checked: false,
                disabled: true,
            });
        }

        if (isFake) {
            this.#$hostingPowerPackAdvert
                .find('.power-pack-advert-hosting-type')
                .text(this.#$hostingType.find(':selected').text());
        }

        this.#$hostingPowerPackAdvert.toggle(isFake);
        this.#$hostingAccountRow.toggle(onHostingService && !isFake);
        this.#$toolRow.toggle(!isFake);

        this.#hostingServiceView?.remove();
        this.#hostingServiceView = null;

        if (info !== null) {
            const hostingType = model.get('hostingType');
            const ViewClass = (this.#hostingServiceViews[hostingType] ??
                               HostingServiceRepositoryFormView);

            this.#hostingServiceView = new ViewClass({
                data: info.js_view_data,
                el: this.el,
                model: model,
            });
            this.#hostingServiceView.render();
        }

        this.#rebuildToolList();
        this.#rebuildAccountList();
        this.#rebuildPlanList();
        this._updateHostingAuthForms();
        this._updateHostingRepoForms();
        this._updateSCMToolForms();
    }

    /**
     * Rebuild the Repository Type field for the selected hosting service.
     *
     * Only the SCMTools supported by the service are listed. All are listed
     * when no hosting service is selected.
     */
    #rebuildToolList() {
        const model = this.model;
        const info = model.getHostingServiceInfo();
        const $tool = this.#$tool;
        const currentTool = model.get('tool');
        const supported: string[] = info?.scmtools ?? [];

        $tool.empty();

        for (const option of this.#toolOptions) {
            if (supported.length === 0 ||
                supported.includes(option.text) ||
                supported.includes(option.value)) {
                $('<option>')
                    .text(option.text)
                    .val(option.value)
                    .appendTo($tool);
            }
        }

        if ($tool.children(`[value="${currentTool}"]`).length > 0) {
            $tool.val(currentTool);
        }

        model.set('tool', $tool.val() as string, {silent: true});
    }

    /**
     * Rebuild the Hosting Account field for the selected hosting service.
     *
     * The previously-selected account is kept if it's still listed.
     * Otherwise, the first account is selected, unless the user needs to
     * fill out the authentication form (for a two-factor auth code or to
     * correct errors).
     */
    #rebuildAccountList() {
        const model = this.model;
        const info = model.getHostingServiceInfo();
        const $hostingAccount = this.#$hostingAccount;
        const selectedID = model.get('hostingAccountID');
        let accountID: (number | null) = null;

        $hostingAccount.children('option[value!=""]').remove();

        if (info !== null && info.fake !== true) {
            const accounts = info.accounts;
            const keepEmpty = (
                info.needs_two_factor_auth_code ||
                this.#getHostingAuthForm().find('.errorlist').length > 0);

            for (const account of accounts) {
                $('<option>')
                    .val(account.pk)
                    .text(this.#hostingServiceView.getAccountLabel(account))
                    .appendTo($hostingAccount);
            }

            if (accounts.some(account => (account.pk === selectedID))) {
                accountID = selectedID;
            } else if (!keepEmpty && accounts.length > 0) {
                accountID = accounts[0].pk;
            }
        }

        $hostingAccount.val(accountID === null ? '' : String(accountID));
        model.set('hostingAccountID', accountID, {silent: true});
    }

    /**
     * Rebuild the Repository Plan field for the selected hosting service.
     *
     * The previously-selected plan is kept if it's still listed. The row
     * is only shown when there's more than one plan to choose from.
     */
    #rebuildPlanList() {
        const model = this.model;
        const info = model.getHostingServiceInfo();
        const $repoPlan = this.#$repoPlan;
        const selectedPlan = model.get('repositoryPlan');
        let plans = [];

        if (info !== null) {
            plans = this.#hostingServiceView.getRepositoryPlans(
                info.plans,
                this.model.getSelectedAccount());
        }

        $repoPlan.empty();

        for (const plan of plans) {
            $('<option>')
                .val(plan.id)
                .text(plan.label)
                .appendTo($repoPlan);
        }

        if (plans.some(plan => (plan.id === selectedPlan))) {
            $repoPlan.val(selectedPlan);
        }

        this.#$repoPlanRow.toggle(plans.length > 1 &&
                                  !model.isFakeHostingService());
        model.set('repositoryPlan',
                  ($repoPlan.val() as string) || null,
                  {silent: true});
    }

    /**
     * Update the form for a newly-selected hosting account.
     *
     * The hosting service's view may offer different plans for the
     * account, so the plans are rebuilt.
     */
    private _onModelHostingAccountChanged() {
        this._updateHostingAuthForms();
        this.#rebuildPlanList();
        this._updateHostingRepoForms();
    }

    /**
     * Return the authentication sub-form for the selected hosting service.
     *
     * Returns:
     *     jQuery:
     *     The sub-form, which may be empty.
     */
    #getHostingAuthForm(): JQuery {
        const hostingType = this.model.get('hostingType');

        return this.$(`#hosting-auth-form-${hostingType}`);
    }

    /**
     * Show the authentication fields for the selected hosting account.
     *
     * The authentication sub-form is shown when linking a new account, when
     * a two-factor auth code is needed, or when the selected account must
     * be re-authorized. Otherwise, the user can choose to edit the
     * account's credentials.
     */
    private _updateHostingAuthForms() {
        const model = this.model;
        const info = model.getHostingServiceInfo();

        this.#$hostingAuthForms.hide();
        this.#$hostingAccountRelink.hide();
        this.#$editCredentials.hide();
        this.#$editCredentialsLabel.text(_`Edit credentials`);
        this.#$forceAuth.val('false');

        if (info === null || info.fake === true) {
            return;
        }

        const $authForm = this.#getHostingAuthForm();
        const needs2FA = info.needs_two_factor_auth_code;

        /* Hide any fields required for 2FA unless explicitly needed. */
        $authForm.find('[data-required-for-2fa]').closest('.form-row')
            .toggle(needs2FA);

        const account = model.getSelectedAccount();

        if (account === null) {
            /* Present fields for linking a new account. */
            $authForm.show();
        } else if (needs2FA) {
            /*
             * The user needs to enter a 2FA code. Show the auth form, and
             * make sure we force authentication.
             */
            this.#$forceAuth.val('true');
            $authForm.show();
        } else if (account.is_authorized &&
                   $authForm.find('.errorlist').length === 0) {
            this.#$editCredentials.show();
        } else {
            $authForm.show();
            this.#$hostingAccountRelink.show();
        }
    }

    /**
     * Show the repository sub-form for the selected hosting service plan.
     */
    private _updateHostingRepoForms() {
        const model = this.model;
        const hostingType = model.get('hostingType');
        const plan = model.get('repositoryPlan') || 'default';

        this.#$hostingRepoForms.hide();
        this.$(`#repo-form-hosting-${hostingType}-${plan}`).show();
    }

    /**
     * Show the sub-forms for the selected SCMTool.
     *
     * These only apply when no hosting service is selected.
     */
    private _updateSCMToolForms() {
        const model = this.model;
        let isFakeTool = false;

        this.#$scmtoolAuthForms.hide();
        this.#$scmtoolRepoForms.hide();

        this.#scmToolView?.remove();
        this.#scmToolView = null;

        if (!model.isHostingServiceSelected()) {
            const toolID = model.get('tool');
            const toolInfo = model.get('tools')[toolID];

            isFakeTool = (toolInfo?.fake === true);

            if (isFakeTool) {
                this.#$toolPowerPackAdvert
                    .find('.power-pack-advert-hosting-type')
                    .text(toolInfo.name);
            } else {
                this.$(`#auth-form-scm-${toolID}`).show();
                this.$(`#repo-form-scm-${toolID}`).show();

                const ViewClass = (this.#scmToolViews[toolID] ??
                                   SCMToolRepositoryFormView);

                this.#scmToolView = new ViewClass({
                    el: this.el,
                    model: model,
                });
                this.#scmToolView.render();
            }
        }

        this.#$toolPowerPackAdvert.toggle(isFakeTool);
        this.#$submitButtons.prop(
            'disabled',
            isFakeTool || model.isFakeHostingService());
    }

    /**
     * Show the access list fields only when the repository isn't public.
     */
    private _updatePublicAccess() {
        const visible = !this.$('#id_public').prop('checked');

        this.$('#row-users').toggle(visible);
        this.$('#row-review_groups').toggle(visible);
    }

    /**
     * Handle a click on the link for editing credentials.
     *
     * This toggles the hosting service's authentication sub-form, and
     * whether the account will be re-authorized on save.
     *
     * Returns:
     *     boolean:
     *     ``false``, to prevent the default action.
     */
    private _onEditCredentialsClicked(): boolean {
        const $authForm = this.#getHostingAuthForm();

        if (this.#$forceAuth.val() === 'true') {
            this.#$editCredentialsLabel.text(_`Edit credentials`);
            $authForm.hide();
            this.#$forceAuth.val('false');
        } else {
            this.#$editCredentialsLabel.text(
                gettext('Cancel editing credentials'));
            $authForm.show();
            this.#$forceAuth.val('true');
        }

        return false;
    }
}
