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

function updateFormDisplay(id, fields) {
    var type = $("#id_" + id)[0].value,
        i;

    for (i in fields[prevTypes[id]]) {
        $("#row-" + fields[prevTypes[id]][i]).hide();
    }

    for (i in fields[type]) {
        $("#row-" + fields[type][i]).show();
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
    var fields = TOOLS_FIELDS["none"];

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
        hostingAccountEl = $("#id_hosting_account"),
        hostingAccountRowEl = $("#row-hosting_account"),
        hostingAccountUserRowEl = $("#row-hosting_account_username"),
        hostingAccountPassRowEl = $("#row-hosting_account_password"),
        bugTrackerUseHostingEl = $("#id_bug_tracker_use_hosting"),
        bugTrackerTypeEl = $("#id_bug_tracker_type"),
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
                selectedAccount;

            updateRepositoryType();

            if (hostingType === "custom") {
                repoPlanRowEl.hide();
                repoPathRowEl.show();
                repoMirrorPathRowEl.show();
            } else {
                var accounts = HOSTING_SERVICES[hostingType].accounts,
                    i;

                hideAllToolsFields();
                repoPathRowEl.hide();
                repoMirrorPathRowEl.hide();

                updatePlanEl(repoPlanRowEl, repoPlanEl, hostingType);

                /* Rebuild the list of accounts. */
                selectedAccount = parseInt(hostingAccountEl.val(), 10);
                hostingAccountEl.find('option[value!=""]').remove();

                for (i = 0; i < accounts.length; i++) {
                    var account = accounts[i],
                        opt = $("<option/>")
                            .val(account.pk)
                            .text(account.username)
                            .appendTo(hostingAccountEl);

                    if (account.pk === selectedAccount) {
                        opt.attr("selected", "selected");
                    }
                }
            }

            repoPlanEl.triggerHandler("change");

            if (hostingType === "custom" ||
                !HOSTING_SERVICES[hostingType].supports_bug_trackers) {
                bugTrackerUseHostingEl[0].disabled = true;
                bugTrackerUseHostingEl[0].checked = false;
                bugTrackerUseHostingEl.triggerHandler("change");
            } else {
                bugTrackerUseHostingEl[0].disabled = false;
            }
        })
        .triggerHandler("change");

    $([hostingTypeEl[0], hostingAccountEl[0]])
        .change(function() {
            var hostingType = hostingTypeEl.val();

            if (hostingType === "custom") {
                hostingAccountRowEl.hide();
                hostingAccountUserRowEl.hide();
                hostingAccountPassRowEl.hide();
            } else {
                hostingAccountRowEl.show();

                if (hostingAccountEl.val() === "") {
                    hostingAccountUserRowEl.show();

                    if (HOSTING_SERVICES[hostingType].needs_authorization) {
                        hostingAccountPassRowEl.show();
                    } else {
                        hostingAccountPassRowEl.hide();
                    }
                } else {
                    hostingAccountUserRowEl.hide();
                    hostingAccountPassRowEl.hide();
                }
            }
        })
        .triggerHandler("change");

    toolEl
        .change(function() {
            if (hostingTypeEl[0].value === "custom") {
                updateFormDisplay("tool", TOOLS_FIELDS);
            } else {
                hideAllToolsFields();
            }
        })
        .triggerHandler("change");

    bugTrackerTypeEl
        .change(function() {
            var bugTrackerType = bugTrackerTypeEl[0].value;

            bugTrackerForms.hide();

            if (bugTrackerType === 'custom') {
                bugTrackerPlanRowEl.hide();
                bugTrackerUsernameRowEl.hide();
                bugTrackerURLRowEl.show();
            } else if (bugTrackerType === 'none') {
                bugTrackerPlanRowEl.hide();
                bugTrackerUsernameRowEl.hide();
                bugTrackerURLRowEl.hide();
            } else {
                bugTrackerURLRowEl.hide();
                updatePlanEl(bugTrackerPlanRowEl, bugTrackerPlanEl,
                             bugTrackerType);
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

