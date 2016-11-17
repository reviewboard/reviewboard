var prevTypes = {},
    origRepoTypes = [],
    powerPackTemplate = [
        '<h3>', gettext('Power Pack Required'), '</h3>',
        '<p>',
        gettext('<span class="power-pack-advert-hosting-type"></span> support is available with <a href="https://www.reviewboard.org/powerpack/">Power Pack</a>, an extension which also offers powerful reports, document review, and more.'),
        '</p>'
    ].join('');

function updateFormDisplay(id, tools_info) {
    var type = $('#id_' + id).val(),
        oldInfo = tools_info[prevTypes[id]],
        newInfo = tools_info[type],
        text,
        field,
        i;

    for (i = 0; i < oldInfo.fields.length; i++) {
        $('#row-' + oldInfo.fields[i]).hide();
    }

    for (field in oldInfo.help_text) {
        $('#row-' + field).find('p.help')
            .remove();
    }

    for (i = 0; i < newInfo.fields.length; i++) {
        $('#row-' + newInfo.fields[i]).show();
    }

    for (field in newInfo.help_text) {
        if (newInfo.help_text.hasOwnProperty(field)) {
            text = newInfo.help_text[field];

            $('<p class="help"/>')
                .text(text)
                .appendTo($('#row-' + field));
        }
    }

    prevTypes[id] = type;
}

function updatePlanEl($row, $plan, serviceType, isFake) {
    var planTypes = HOSTING_SERVICES[serviceType].plans,
        selectedPlan = $plan.val(),
        planType,
        opt,
        i;

    $plan.empty();

    if (planTypes.length === 1 || isFake) {
        $row.hide();
    } else {
        for (i = 0; i < planTypes.length; i++) {
            planType = planTypes[i];
            opt = $('<option/>')
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
    var formID = formPrefix + '-' + $hostingType.val() + '-' +
                 ($plan.val() || 'default');

    $forms.hide();
    $('#' + formID).show();
}

function hideAllToolsFields() {
    var fields = TOOLS_INFO.none.fields,
        i;

    for (i = 0; i < fields.length; i++) {
        $('#row-' + fields[i]).hide();
    }
}

function updateRepositoryType() {
    var hostingType = $('#id_hosting_type').val(),
        newRepoTypes = (hostingType === 'custom'
                        ? []
                        : HOSTING_SERVICES[hostingType].scmtools),
        $repoTypes = $('#id_tool'),
        currentRepoType = $repoTypes.val();

    $repoTypes.empty();

    $(origRepoTypes).each(function (i) {
        var repoType = origRepoTypes[i];

        if (newRepoTypes.length === 0 ||
            newRepoTypes.indexOf(repoType.text) !== -1) {
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
    var hostingType = $('#id_hosting_type').val(),
        $hostingAccount = $('#id_hosting_account'),
        $authForm = $('#hosting-auth-form-' + hostingType),
        hostingInfo = HOSTING_SERVICES[hostingType],
        accounts = hostingInfo.accounts,
        selectedAccount = parseInt($hostingAccount.val(), 10),
        foundSelected = false,
        $opt,
        account,
        text,
        i;

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

    for (i = 0; i < accounts.length; i++) {
        account = accounts[i];
        text = account.username;

        if (account.hosting_url) {
            text += ' (' + account.hosting_url + ')';
        }

        $opt = $('<option/>')
            .val(account.pk)
            .text(text)
            .data('account', account)
            .appendTo($hostingAccount);

        if (account.pk === selectedAccount || !foundSelected) {
            $opt.prop('selected', true);
            foundSelected = true;
            $hostingAccount.triggerHandler('change');
        }
    }
}

$(document).ready(function() {
    var $hostingType = $('#id_hosting_type'),
        $hostingAuthForms = $('.hosting-auth-form'),
        $hostingAccount = $('#id_hosting_account'),
        $hostingAccountRow = $('#row-hosting_account'),
        $hostingAccountRelink = $('<p/>')
            .text(gettext('The authentication requirements for this account have changed. You will need to re-authenticate.'))
            .addClass('errornote')
            .hide()
            .appendTo($hostingAccountRow),
        $associateSshKeyFieldset =
            $('#row-associate_ssh_key').parents('fieldset'),
        $associateSshKey = $('#id_associate_ssh_key'),
        associateSshKeyDisabled = $associateSshKey.prop('disabled'),
        $bugTrackerUseHosting = $('#id_bug_tracker_use_hosting'),
        $bugTrackerType = $('#id_bug_tracker_type'),
        $bugTrackerHostingURLRow = $('#row-bug_tracker_hosting_url'),
        $bugTrackerTypeRow = $('#row-bug_tracker_type'),
        $bugTrackerPlan = $('#id_bug_tracker_plan'),
        $bugTrackerPlanRow = $('#row-bug_tracker_plan'),
        $bugTrackerURLRow = $('#row-bug_tracker'),
        $bugTrackerUsernameRow =
            $('#row-bug_tracker_hosting_account_username'),
        $repoPathRow = $('#row-path'),
        $repoMirrorPathRow = $('#row-mirror_path'),
        $repoPlanRow = $('#row-repository_plan'),
        $repoPlan = $('#id_repository_plan'),
        $publicAccess = $('#id_public'),
        $tool = $('#id_tool'),
        $toolRow = $('#row-tool'),
        $publicKeyPopup = $('#ssh-public-key-popup'),
        $repoForms = $('.repo-form'),
        $bugTrackerForms = $('.bug-tracker-form'),
        $submitButtons = $('input[type="submit"]'),
        $editHostingCredentials = $('#repo-edit-hosting-credentials'),
        $editHostingCredentialsLabel =
            $('#repo-edit-hosting-credentials-label'),
        $forceAuth = $('#id_force_authorize'),
        $powerPackAdvert = $('<div class="powerpack-advert" />')
            .html(powerPackTemplate)
            .hide()
            .appendTo($hostingType.closest('fieldset'));

    prevTypes.bug_tracker_type = 'none';
    prevTypes.hosting_type = 'custom';
    prevTypes.tool = 'none';

    $tool.find('option').each(function() {
        var $repoType = $(this);

        origRepoTypes.push({
            value: $repoType.val(),
            text: $repoType.text()
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

    $repoPlan.change(function() {
        updateHostingForm($hostingType, 'repo-form', $repoPlan, $repoForms);
    });

    $bugTrackerPlan.change(function() {
        var plan = $bugTrackerPlan.val() || 'default',
            bugTrackerType = $bugTrackerType.val(),
            planInfo = HOSTING_SERVICES[bugTrackerType].planInfo[plan];

        updateHostingForm($bugTrackerType, 'bug-tracker-form',
                          $bugTrackerPlan, $bugTrackerForms);

        $bugTrackerUsernameRow.setVisible(
            planInfo.bug_tracker_requires_username);
    });

    $hostingType
        .change(function() {
            var hostingType = $hostingType.val(),
                isCustom = (hostingType === 'custom'),
                isFake = (!isCustom &&
                          HOSTING_SERVICES[hostingType].fake === true);

            updateRepositoryType();

            if (isCustom) {
                $repoPlanRow.hide();
                $repoPathRow.show();
                $repoMirrorPathRow.show();
            } else {
                hideAllToolsFields();
                $repoPathRow.hide();
                $repoMirrorPathRow.hide();

                updatePlanEl($repoPlanRow, $repoPlan, hostingType, isFake);
            }

            $repoPlan.triggerHandler('change');

            if (isCustom ||
                !HOSTING_SERVICES[hostingType].supports_bug_trackers) {
                $bugTrackerUseHosting
                    .prop({
                        disabled: true,
                        checked: false
                    })
                    .triggerHandler('change');
            } else {
                $bugTrackerUseHosting.prop('disabled', false);
            }

            if (isCustom ||
                !HOSTING_SERVICES[hostingType].supports_ssh_key_association) {
                $associateSshKeyFieldset.hide();
                $associateSshKey.prop({
                    disabled: true,
                    checked: false
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

            $bugTrackerTypeRow.setVisible(!isFake);
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
        .change(function() {
            var hostingType = $hostingType.val(),
                hostingInfo,
                selectedIndex,
                account,
                $authForm,
                $twoFactorAuthRows,
                $selectedOption;

            $hostingAuthForms.hide();
            $hostingAccountRelink.hide();
            $editHostingCredentials
                .hide()
                .val(gettext('Edit credentials'));
            $forceAuth.val('false');

            if (hostingType === 'custom') {
                $hostingAccountRow.hide();
            } else {
                hostingInfo = HOSTING_SERVICES[hostingType];

                if (hostingInfo.fake !== true) {
                    $hostingAccountRow.show();

                    $authForm = $('#hosting-auth-form-' + hostingType);

                    /*
                     * Hide any fields required for 2FA unless explicitly
                     * needed.
                     */
                    $twoFactorAuthRows =
                        $authForm.find('[data-required-for-2fa]')
                        .closest('.form-row')
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
                        selectedIndex = $hostingAccount[0].selectedIndex;
                        $selectedOption = $($hostingAccount[0]
                            .options[selectedIndex]);
                        account = $selectedOption.data('account');

                        if (account.is_authorized) {
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
        .change(function() {
            if ($hostingType.val() === 'custom') {
                updateFormDisplay('tool', TOOLS_INFO);
            } else {
                hideAllToolsFields();
            }
        })
        .triggerHandler('change');

    $bugTrackerType
        .change(function() {
            var bugTrackerType = $bugTrackerType.val();

            $bugTrackerForms.hide();

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

    $('#show-ssh-key-link').toggle(function() {
        $(this).text(gettext('Hide SSH Public Key'));
        $publicKeyPopup.show();
        return false;
    }, function() {
        $(this).text(gettext('Show SSH Public Key'));
        $publicKeyPopup.hide();
        return false;
    });

    $editHostingCredentials.click(function() {
        var $authForm = $('#hosting-auth-form-' + $hostingType.val());

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
