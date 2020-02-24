(function() {


const prevTypes = {};
const origRepoTypes = [];
const powerPackTemplate = dedent`
    <h3>${gettext('Power Pack Required')}</h3>
    <p>
    ${gettext('<span class="power-pack-advert-hosting-type"></span> support is available with <a href="https://www.reviewboard.org/powerpack/">Power Pack</a>, an extension which also offers powerful reports, document review, and more.')}
    </p>
`;
const gerritPluginRequiredTemplate = dedent`
    <h3>
    ${gettext('Plugin Required')}
    </h3>
    <p>
    ${interpolate(
        gettext('The <code>gerrit-reviewboard</code> plugin is required for Gerrit integration. See the <a href="%s" target="_blank">instructions</a> for installing the plugin on your server.'),
        [MANUAL_URL + 'admin/configuration/repositories/gerrit/'])}
    </p>
`;


function updatePlanEl($row, $plan, serviceType, isFake) {
    const planTypes = HOSTING_SERVICES[serviceType].plans;
    const selectedPlan = $plan.val();

    $plan.empty();

    if (planTypes.length === 1 || isFake) {
        $row.hide();
    } else {
        for (let i = 0; i < planTypes.length; i++) {
            const planType = planTypes[i];
            const opt = $('<option/>')
                .val(planType.type)
                .text(planType.label)
                .appendTo($plan);

            if (planType.type === selectedPlan) {
                opt.prop('selected', true);
            }
        }

        $row.show();
    }

    $plan.triggerHandler('change');
}


function updateHostingForm($hostingType, formPrefix, $plan, $forms) {
    const formID = `#${formPrefix}-${$hostingType.val()}-${$plan.val() || 'default'}`;

    $forms.hide();
    $(formID).show();
}


function updateRepositoryType() {
    const hostingType = $('#id_hosting_type').val();
    const newRepoTypes = (hostingType === 'custom'
                          ? []
                          : HOSTING_SERVICES[hostingType].scmtools);
    const $repoTypes = $('#id_tool');
    const currentRepoType = $repoTypes.val();

    $repoTypes.empty();

    origRepoTypes.forEach(repoType => {
        if (newRepoTypes.length === 0 ||
            newRepoTypes.indexOf(repoType.text) !== -1 ||
            newRepoTypes.indexOf(repoType.value) !== -1) {
            $('<option/>')
                .text(repoType.text)
                .val(repoType.value)
                .appendTo($repoTypes);

            if (repoType.value === currentRepoType) {
                $repoTypes.val(currentRepoType);
            }
        }
    });

    $repoTypes.triggerHandler('change');
}


function updateAccountList() {
    const hostingType = $('#id_hosting_type').val();
    const $hostingAccount = $('#id_hosting_account');
    const $authForm = $('#hosting-auth-form-' + hostingType);
    const hostingInfo = HOSTING_SERVICES[hostingType];
    const accounts = hostingInfo.accounts;
    const selectedAccount = parseInt($hostingAccount.val(), 10);
    let foundSelected = false;

    /* Rebuild the list of accounts. */
    $hostingAccount.find('option[value!=""]').remove();

    if (hostingInfo.needs_two_factor_auth_code ||
        $authForm.find('.errorlist').length > 0) {
        /*
         * The first one will be selected automatically, which
         * we want. Don't select any below.
         */
        foundSelected = true;
    }

    accounts.forEach(account => {
        let text = account.username;

        if (account.hosting_url) {
            text += ` (${account.hosting_url})`;
        }

        const $opt = $('<option/>')
            .val(account.pk)
            .text(text)
            .data('account', account)
            .appendTo($hostingAccount);

        if (account.pk === selectedAccount || !foundSelected) {
            $opt.prop('selected', true);
            foundSelected = true;
            $hostingAccount.triggerHandler('change');
        }
    });
}


$(document).ready(function() {
    const $hostingType = $('#id_hosting_type');
    const $hostingAuthForms = $('.hosting-auth-form');
    const $hostingRepoForms = $('.hosting-repo-form');
    const $hostingAccount = $('#id_hosting_account');
    const $hostingAccountRow = $('#row-hosting_account');
    const $hostingAccountRelink = $('<p/>')
        .text(gettext('The authentication requirements for this account have changed. You will need to re-authenticate.'))
        .addClass('errornote')
        .hide()
        .appendTo($hostingAccountRow);
    const $scmtoolAuthForms = $('.scmtool-auth-form');
    const $scmtoolRepoForms = $('.scmtool-repo-form');
    const $associateSshKeyFieldset =
        $('#row-associate_ssh_key').parents('fieldset');
    const $associateSshKey = $('#id_associate_ssh_key');
    const associateSshKeyDisabled = $associateSshKey.prop('disabled');
    const $bugTrackerUseHosting = $('#id_bug_tracker_use_hosting');
    const $bugTrackerUseHostingRow = $('#row-bug_tracker_use_hosting');
    const $bugTrackerType = $('#id_bug_tracker_type');
    const $bugTrackerHostingURLRow = $('#row-bug_tracker_hosting_url');
    const $bugTrackerTypeRow = $('#row-bug_tracker_type');
    const $bugTrackerPlan = $('#id_bug_tracker_plan');
    const $bugTrackerPlanRow = $('#row-bug_tracker_plan');
    const $bugTrackerURLRow = $('#row-bug_tracker');
    const $bugTrackerUsernameRow =
        $('#row-bug_tracker_hosting_account_username');
    const $repoPlanRow = $('#row-repository_plan');
    const $repoPlan = $('#id_repository_plan');
    const $publicAccess = $('#id_public');
    const $tool = $('#id_tool');
    const $toolRow = $('#row-tool');
    const $showSshKey = $('#show-ssh-key-link');
    const $publicKeyPopup = $('#ssh-public-key-popup');
    const $bugTrackerForms = $('.bug-tracker-form');
    const $submitButtons = $('input[type="submit"]');
    const $editHostingCredentials = $('#repo-edit-hosting-credentials');
    const $editHostingCredentialsLabel =
        $('#repo-edit-hosting-credentials-label');
    const $forceAuth = $('#id_force_authorize');
    const $powerPackAdvert = $('<div class="powerpack-advert" />')
        .html(powerPackTemplate)
        .hide()
        .appendTo($hostingType.closest('fieldset'));
    const $gerritPluginInfo = $('<div class="gerrit-plugin-advert" />')
        .html(gerritPluginRequiredTemplate)
        .hide()
        .appendTo($('#row-hosting_type'));

    prevTypes.bug_tracker_type = 'none';
    prevTypes.hosting_type = 'custom';
    prevTypes.tool = 'none';

    $tool.find('option').each((i, el) => {
        const $repoType = $(el);

        origRepoTypes.push({
            value: $repoType.val(),
            text: $repoType.text(),
        });
    });

    $bugTrackerUseHosting
        .change(function() {
            if (this.checked) {
                $bugTrackerTypeRow.hide();
                $bugTrackerPlanRow.hide();
                $bugTrackerUsernameRow.hide();
                $bugTrackerURLRow.hide();
                $bugTrackerForms.hide();
            } else {
                $bugTrackerTypeRow.show();
                $bugTrackerType.triggerHandler('change');
            }
        })
        .triggerHandler('change');

    $repoPlan.change(() => updateHostingForm($hostingType, 'repo-form-hosting',
                                             $repoPlan, $hostingRepoForms));

    $bugTrackerPlan.change(() => {
        const plan = $bugTrackerPlan.val() || 'default';
        const bugTrackerType = $bugTrackerType.val();
        const planInfo = HOSTING_SERVICES[bugTrackerType].planInfo[plan];

        updateHostingForm($bugTrackerType, 'bug-tracker-form-hosting',
                          $bugTrackerPlan, $bugTrackerForms);

        $bugTrackerUsernameRow.setVisible(
            planInfo.bug_tracker_requires_username);
    });

    $hostingType
        .change(() => {
            const hostingType = $hostingType.val();
            const isCustom = (hostingType === 'custom');
            const isFake = (!isCustom &&
                            HOSTING_SERVICES[hostingType].fake === true);

            updateRepositoryType();

            $gerritPluginInfo.toggle(hostingType === 'gerrit');

            if (isCustom) {
                $repoPlanRow.hide();
            } else {
                $scmtoolAuthForms.hide();
                $scmtoolRepoForms.hide();

                updatePlanEl($repoPlanRow, $repoPlan, hostingType, isFake);
            }

            $repoPlan.triggerHandler('change');

            if (isCustom ||
                isFake ||
                !HOSTING_SERVICES[hostingType].supports_bug_trackers) {
                $bugTrackerUseHostingRow.hide();
                $bugTrackerUseHosting
                    .prop({
                        disabled: true,
                        checked: false,
                    })
                    .triggerHandler('change');
            } else {
                $bugTrackerUseHosting.prop('disabled', false);
                $bugTrackerUseHostingRow.show();
            }

            if (isCustom ||
                !HOSTING_SERVICES[hostingType].supports_ssh_key_association) {
                $associateSshKeyFieldset.hide();
                $associateSshKey.prop({
                    disabled: true,
                    checked: false,
                });
            } else {
                /*
                 * Always use the original state of the checkbox (i.e. the
                 * state on page load)
                 */
                $associateSshKey.prop('disabled', associateSshKeyDisabled);
                $associateSshKeyFieldset.show();
            }

            if (isFake) {
                $powerPackAdvert
                    .find('.power-pack-advert-hosting-type')
                    .text($hostingType.find(':selected').text());
            }

            $hostingAccountRow.setVisible(!isFake);
            $toolRow.setVisible(!isFake);

            $powerPackAdvert.setVisible(isFake);
            $submitButtons.prop('disabled', isFake);

            if (!isCustom) {
                updateAccountList();
            }
        })
        .triggerHandler('change');

    $([$hostingType[0], $hostingAccount[0]])
        .change(() => {
            $hostingAuthForms.hide();
            $hostingAccountRelink.hide();
            $editHostingCredentials
                .hide()
                .val(gettext('Edit credentials'));
            $forceAuth.val('false');

            const hostingType = $hostingType.val();

            if (hostingType === 'custom') {
                $hostingAccountRow.hide();
            } else {
                const hostingInfo = HOSTING_SERVICES[hostingType];

                if (hostingInfo.fake !== true) {
                    $hostingAccountRow.show();

                    const $authForm = $('#hosting-auth-form-' + hostingType);

                    /*
                     * Hide any fields required for 2FA unless explicitly
                     * needed.
                     */
                    $authForm.find('[data-required-for-2fa]').closest('.form-row')
                        .setVisible(hostingInfo.needs_two_factor_auth_code);

                    if ($hostingAccount.val() === '') {
                        /* Present fields for linking a new account. */
                        $authForm.show();
                    } else if (hostingInfo.needs_two_factor_auth_code) {
                        /*
                         * The user needs to enter a 2FA code. We need to
                         * show the auth form, and ensure we will be forcing
                         * authentication.
                         */
                        $forceAuth.val('true');
                        $authForm.show();
                    } else {
                        /* An existing linked account has been selected. */
                        const selectedIndex = $hostingAccount[0].selectedIndex;
                        const $selectedOption =
                            $($hostingAccount[0].options[selectedIndex]);
                        const account = $selectedOption.data('account');

                        if (account.is_authorized &&
                            $authForm.find('.errorlist').length === 0) {
                            $editHostingCredentials.show();
                        } else {
                            $authForm.show();
                            $hostingAccountRelink.show();
                        }
                    }
                }
            }
        })
        .triggerHandler('change');

    $tool
        .change(() => {
            if ($hostingType.val() === 'custom') {
                var scmtoolID = $('#id_tool').val(),
                    $authForm = $('#auth-form-scm-' + scmtoolID),
                    $repoForm = $('#repo-form-scm-' + scmtoolID);

                $scmtoolAuthForms.hide();
                $scmtoolRepoForms.hide();

                $authForm.show();
                $repoForm.show();
            }
        })
        .triggerHandler('change');

    $bugTrackerType
        .change(() => {
            $bugTrackerForms.hide();

            const bugTrackerType = $bugTrackerType.val();

            if (bugTrackerType === 'custom' || bugTrackerType === 'none') {
                $bugTrackerHostingURLRow.hide();
                $bugTrackerPlanRow.hide();
                $bugTrackerUsernameRow.hide();
            }

            if (bugTrackerType === 'custom') {
                $bugTrackerURLRow.show();
            } else if (bugTrackerType === 'none') {
                $bugTrackerURLRow.hide();
            } else {
                $bugTrackerURLRow.hide();
                updatePlanEl($bugTrackerPlanRow, $bugTrackerPlan,
                             bugTrackerType, false);

                $bugTrackerHostingURLRow.setVisible(
                    HOSTING_SERVICES[bugTrackerType].self_hosted);
            }
        })
        .triggerHandler('change');

    $publicAccess
        .change(function() {
            var visible = !this.checked;
            $('#row-users').setVisible(visible);
            $('#row-review_groups').setVisible(visible);
        })
        .triggerHandler('change');

    $showSshKey.on('click', () => {
        if ($publicKeyPopup.is(':visible')) {
            $showSshKey.text(gettext('Show your SSH public key'));
            $publicKeyPopup.hide();
        } else {
            $showSshKey.text(gettext('Hide your SSH public key'));
            $publicKeyPopup.show();
        }

        return false;
    });

    $editHostingCredentials.click(() => {
        let $authForm = $('#hosting-auth-form-' + $hostingType.val());

        if ($forceAuth.val() === 'true') {
            $editHostingCredentialsLabel.text(gettext('Edit credentials'));
            $authForm.hide();
            $forceAuth.val('false');
        } else {
            $editHostingCredentialsLabel.text(
                gettext('Cancel editing credentials'));
            $authForm = $('#hosting-auth-form-' + $hostingType.val()).show();
            $authForm.show();
            $forceAuth.val('true');
        }

        return false;
    });
});


})();
