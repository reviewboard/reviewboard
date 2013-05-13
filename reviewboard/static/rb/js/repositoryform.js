var prevTypes = {},
    origRepoTypes = [];

function forEachField(fields, wholeRows, func) {
    var prefix = (wholeRows ? "#id_" : "#row-"),
        id,
        field;

    for (id in fields) {
        for (field in fields[id]) {
            func($(prefix + fields[id][field]));
        }
    }
}

function updateFormDisplay(id, tools_info) {
    var type = $("#id_" + id)[0].value,
        oldInfo = tools_info[prevTypes[id]],
        newInfo = tools_info[type],
        field,
        i;

    for (i = 0; i < oldInfo.fields.length; i++) {
        $("#row-" + oldInfo.fields[i]).hide();
    }

    for (field in oldInfo.help_text) {
        $("#row-" + field).find('p.help')
            .remove();
    }

    for (i = 0; i < newInfo.fields.length; i++) {
        $("#row-" + newInfo.fields[i]).show();
    }

    for (field in newInfo.help_text) {
        var text = newInfo.help_text[field];

        $("#row-" + field)
            .append($('<p class="help"/>')
                .text(text))
    }


    prevTypes[id] = type;
}

function updatePlanEl(rowEl, planEl, serviceType) {
    var planTypes = HOSTING_SERVICES[serviceType].plans,
        selectedPlan = planEl.val(),
        i;

    planEl.empty();

    if (planTypes.length === 1) {
        rowEl.hide();
    } else {
        for (i = 0; i < planTypes.length; i++) {
            var planType = planTypes[i],
                opt = $('<option/>')
                    .val(planType.type)
                    .text(planType.label)
                    .appendTo(planEl);

            if (planType.type === selectedPlan) {
                opt.attr('selected', 'selected');
            }
        }

        rowEl.show();
    }

    planEl.triggerHandler('change');
}

function updateHostingForm(hostingTypeEl, formPrefix, planEl, formsEl) {
    var formID = formPrefix + "-" + hostingTypeEl[0].value + "-" +
                 (planEl.val() || "default");

    formsEl.hide();
    $("#" + formID).show();
}

function hideAllToolsFields() {
    var fields = TOOLS_INFO["none"].fields;

    for (i = 0; i < fields.length; i++) {
        $("#row-" + fields[i]).hide();
    }
}

function updateRepositoryType() {
    var hostingType = $("#id_hosting_type")[0].value,
        newRepoTypes = (hostingType === "custom"
                        ? []
                        : HOSTING_SERVICES[hostingType].scmtools),
        repoTypesEl = $("#id_tool"),
        currentRepoType = repoTypesEl[0].value;

    repoTypesEl.empty();

    $(origRepoTypes).each(function(i) {
        var repoType = origRepoTypes[i];

        if (newRepoTypes.length === 0 ||
            $.inArray(repoType.text, newRepoTypes) !== -1) {
            $("<option/>")
                .text(repoType.text)
                .val(repoType.value)
                .appendTo(repoTypesEl);

            if (repoType.value === currentRepoType) {
                repoTypesEl[0].value = currentRepoType;
            }
        }
    });

    repoTypesEl.triggerHandler("change");
}

$(document).ready(function() {
    var hostingTypeEl = $("#id_hosting_type"),
        hostingURLRowEl = $("#row-hosting_url"),
        hostingURLEl = $("#id_hosting_url"),
        hostingAccountEl = $("#id_hosting_account"),
        hostingAccountRowEl = $("#row-hosting_account"),
        hostingAccountUserRowEl = $("#row-hosting_account_username"),
        hostingAccountPassRowEl = $("#row-hosting_account_password"),
        hostingAccountRelinkEl = $("<p/>")
            .text('The authentication requirements for this account has ' +
                  'changed. You will need to re-authenticate.')
            .addClass('errornote')
            .hide()
            .appendTo(hostingAccountRowEl),
        associateSshKeyFieldsetEl = $("#row-associate_ssh_key").parent("fieldset"),
        associateSshKeyEl = $("#id_associate_ssh_key"),
        associateSshKeyElDisabled = associateSshKeyEl[0].disabled,
        bugTrackerUseHostingEl = $("#id_bug_tracker_use_hosting"),
        bugTrackerTypeEl = $("#id_bug_tracker_type"),
        bugTrackerHostingURLRowEl = $("#row-bug_tracker_hosting_url"),
        bugTrackerTypeRowEl = $("#row-bug_tracker_type"),
        bugTrackerPlanEl = $("#id_bug_tracker_plan"),
        bugTrackerPlanRowEl = $("#row-bug_tracker_plan"),
        bugTrackerURLRowEl = $("#row-bug_tracker"),
        bugTrackerUsernameRowEl =
            $("#row-bug_tracker_hosting_account_username"),
        repoPathRowEl = $("#row-path"),
        repoMirrorPathRowEl = $("#row-mirror_path"),
        repoPlanRowEl = $("#row-repository_plan"),
        repoPlanEl = $("#id_repository_plan"),
        publicAccessEl = $("#id_public"),
        toolEl = $("#id_tool"),
        publicKeyPopup = $("#ssh-public-key-popup"),
        repoForms = $(".repo-form"),
        bugTrackerForms = $(".bug-tracker-form"),
        service_id;

    prevTypes['bug_tracker_type'] = "none";
    prevTypes['hosting_type'] = "custom";
    prevTypes['tool'] = "none";

    toolEl.find("option").each(function() {
        origRepoTypes.push({value: $(this).val(), text: $(this).text()});
    });

    bugTrackerUseHostingEl
        .change(function() {
            var checked = this.checked;

            if (this.checked) {
                bugTrackerTypeRowEl.hide();
                bugTrackerPlanRowEl.hide();
                bugTrackerUsernameRowEl.hide();
                bugTrackerURLRowEl.hide();
                bugTrackerForms.hide();
            } else {
                bugTrackerTypeRowEl.show();
                bugTrackerTypeEl.triggerHandler('change');
            }
        })
        .triggerHandler("change");

    repoPlanEl.change(function() {
        updateHostingForm(hostingTypeEl, "repo-form", repoPlanEl, repoForms);
    });

    bugTrackerPlanEl.change(function() {
        var plan = bugTrackerPlanEl.val() || 'default',
            bugTrackerType = bugTrackerTypeEl.val(),
            planInfo = HOSTING_SERVICES[bugTrackerType].planInfo[plan];

        updateHostingForm(bugTrackerTypeEl, "bug-tracker-form",
                          bugTrackerPlanEl, bugTrackerForms);

        if (planInfo.bug_tracker_requires_username) {
            bugTrackerUsernameRowEl.show();
        } else {
            bugTrackerUsernameRowEl.hide();
        }
    });

    hostingTypeEl
        .change(function() {
            var hostingType = hostingTypeEl[0].value,
                isCustom = (hostingType === 'custom');

            updateRepositoryType();

            if (isCustom) {
                repoPlanRowEl.hide();
                repoPathRowEl.show();
                repoMirrorPathRowEl.show();
            } else {
                hideAllToolsFields();
                repoPathRowEl.hide();
                repoMirrorPathRowEl.hide();

                updatePlanEl(repoPlanRowEl, repoPlanEl, hostingType);
            }

            repoPlanEl.triggerHandler("change");

            if (isCustom ||
                !HOSTING_SERVICES[hostingType].supports_bug_trackers) {
                bugTrackerUseHostingEl[0].disabled = true;
                bugTrackerUseHostingEl[0].checked = false;
                bugTrackerUseHostingEl.triggerHandler("change");
            } else {
                bugTrackerUseHostingEl[0].disabled = false;
            }

            if (isCustom ||
                !HOSTING_SERVICES[hostingType].supports_ssh_key_association) {
                associateSshKeyFieldsetEl.hide();
                associateSshKeyEl[0].disabled = true;
                associateSshKeyEl[0].checked = false;
            } else {
                /*
                 * Always use the original state of the checkbox (i.e. the
                 * state on page load)
                 */
                associateSshKeyEl[0].disabled = associateSshKeyElDisabled;
                associateSshKeyFieldsetEl.show();
            }

            if (isCustom || !HOSTING_SERVICES[hostingType].self_hosted) {
                hostingURLRowEl.hide();
            } else {
                hostingURLRowEl.show();
            }
        })
        .triggerHandler("change");

    $([hostingTypeEl[0], hostingURLEl[0]])
        .change(function() {
            var hostingType = hostingTypeEl[0].value;

            if (hostingType !== "custom") {
                var accounts = HOSTING_SERVICES[hostingType].accounts,
                    foundSelected = false,
                    selectedAccount,
                    i;

                /* Rebuild the list of accounts. */
                selectedAccount = parseInt(hostingAccountEl.val(), 10);
                selectedURL = hostingURLEl.val() || null;
                hostingAccountEl.find('option[value!=""]').remove();

                for (i = 0; i < accounts.length; i++) {
                    var account = accounts[i];

                    if (account.hosting_url === selectedURL) {
                        var opt = $("<option/>")
                            .val(account.pk)
                            .text(account.username)
                            .data('account', account)
                            .appendTo(hostingAccountEl);

                        if (account.pk === selectedAccount || !foundSelected) {
                            opt.attr("selected", "selected");
                            foundSelected = true;
                            hostingAccountEl.triggerHandler('change');
                        }
                    }
                }
            }
        });

    $([hostingTypeEl[0], hostingAccountEl[0]])
        .change(function() {
            var hostingType = hostingTypeEl.val();

            hostingAccountRelinkEl.hide();

            if (hostingType === "custom") {
                hostingAccountRowEl.hide();
                hostingURLRowEl.hide();
                hostingAccountUserRowEl.hide();
                hostingAccountPassRowEl.hide();
            } else {
                hostingAccountRowEl.show();

                if (HOSTING_SERVICES[hostingType].self_hosted) {
                    hostingURLRowEl.show();
                }

                if (hostingAccountEl.val() === "") {
                    hostingAccountUserRowEl.show();

                    if (HOSTING_SERVICES[hostingType].needs_authorization) {
                        hostingAccountPassRowEl.show();
                    } else {
                        hostingAccountPassRowEl.hide();
                    }
                } else {
                    var selectedOption =
                            $(hostingAccountEl[0].options[
                                hostingAccountEl[0].selectedIndex]),
                        account = selectedOption.data('account');

                    hostingAccountUserRowEl.hide();

                    if (account.is_authorized) {
                        hostingAccountPassRowEl.hide();
                    } else {
                        hostingAccountPassRowEl.show();
                        hostingAccountRelinkEl.show();
                    }
                }
            }
        })
        .triggerHandler("change");

    toolEl
        .change(function() {
            if (hostingTypeEl[0].value === "custom") {
                updateFormDisplay("tool", TOOLS_INFO);
            } else {
                hideAllToolsFields();
            }
        })
        .triggerHandler("change");

    bugTrackerTypeEl
        .change(function() {
            var bugTrackerType = bugTrackerTypeEl[0].value;

            bugTrackerForms.hide();

            if (bugTrackerType === 'custom' || bugTrackerType === 'none') {
                bugTrackerHostingURLRowEl.hide();
                bugTrackerPlanRowEl.hide();
                bugTrackerUsernameRowEl.hide();
            }

            if (bugTrackerType === 'custom') {
                bugTrackerURLRowEl.show();
            } else if (bugTrackerType === 'none') {
                bugTrackerURLRowEl.hide();
            } else {
                bugTrackerURLRowEl.hide();
                updatePlanEl(bugTrackerPlanRowEl, bugTrackerPlanEl,
                             bugTrackerType);


                if (HOSTING_SERVICES[bugTrackerType].self_hosted) {
                    bugTrackerHostingURLRowEl.show();
                } else {
                    bugTrackerHostingURLRowEl.hide();
                }
            }
        })
        .triggerHandler("change");

    publicAccessEl
        .change(function() {
            if (this.checked) {
                $("#row-users").hide();
                $("#row-review_groups").hide();
            } else {
                $("#row-users").show();
                $("#row-review_groups").show();
            }
        })
        .triggerHandler("change");

    $("#show-ssh-key-link").toggle(function() {
        $(this).text("Hide SSH Public Key");
        publicKeyPopup.show();
        return false;
    }, function() {
        $(this).text("Show SSH Public Key");
        publicKeyPopup.hide();
        return false;
    });
});

