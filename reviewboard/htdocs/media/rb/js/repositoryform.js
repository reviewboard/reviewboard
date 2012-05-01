var prevTypes = {};
var origRepoTypes = [];

function forEachField(fields, wholeRows, func) {
    var prefix = (wholeRows ? "#id_" : ".");

    for (var id in fields) {
        for (var field in fields[id]) {
            func($(prefix + fields[id][field]));
        }
    }
}

function updateFormDisplay(id, fields, excludeFields) {
    var type = $("#id_" + id)[0].value;

    for (var i in fields[prevTypes[id]]) {
        $("." + fields[prevTypes[id]][i]).hide();
    }

    for (var i in fields[type]) {
        $("." + fields[type][i]).show();
    }

    if (excludeFields) {
        for (var i in excludeFields) {
            $("." + excludeFields[i]).hide();
        }
    }

    prevTypes[id] = type;
}

function updateRepositoryType() {
    var hostingType = $("#id_hosting_type")[0].value;
    var newRepoTypes = HOSTING_SERVICE_TOOLS[hostingType];

    var repoTypesEl = $("#id_tool");
    var currentRepoType = repoTypesEl[0].value;

    repoTypesEl.empty();

    $(origRepoTypes).each(function(i) {
        var repoType = origRepoTypes[i];

        if (newRepoTypes.length == 0 ||
            $.inArray(repoType.text, newRepoTypes) !== -1) {
            $("<option/>")
                .text(repoType.text)
                .val(repoType.value)
                .appendTo(repoTypesEl);

            if (repoType.value == currentRepoType) {
                repoTypesEl[0].value = currentRepoType;
            }
        }
    });

    updateFormDisplay("tool", TOOLS_FIELDS,
                      HOSTING_SERVICE_HIDDEN_FIELDS[hostingType]);
}

$(document).ready(function() {
    prevTypes['bug_tracker_type'] = "none";
    prevTypes['hosting_type'] = "custom";
    prevTypes['tool'] = "none";

    $("option", "#id_tool").each(function() {
        origRepoTypes.push({value: $(this).val(), text: $(this).text()});
    });

    forEachField(HOSTING_SERVICE_FIELDS, false, function(el) { el.hide(); });
    forEachField(BUG_TRACKER_FIELDS, false, function(el) { el.hide(); });

    var hostingTypeEl = $("#id_hosting_type");
    var hostingProjectNameEl = $("#id_hosting_project_name");
    var bugTrackerUseHostingEl = $("#id_bug_tracker_use_hosting");
    var bugTrackerTypeEl = $("#id_bug_tracker_type");
    var bugTrackerProjectNameEl = $("#id_bug_tracker_project_name");
    var repoNameEl = $("#id_name");
    var repoEl = $("#id_tool");

    var hostingProjectNameDirty = false;
    var bugTrackerProjectNameDirty = false;

    repoNameEl.keyup(function() {
        var value = $(this).val();

        if (!hostingProjectNameDirty) {
            hostingProjectNameEl.val(value);
        }

        if (!bugTrackerProjectNameDirty) {
            bugTrackerProjectNameEl.val(value);
        }
    });

    hostingProjectNameEl
        .keyup(function() {
            hostingProjectNameDirty = ($(this).val() != "");
        })
        .triggerHandler("keyup");

    bugTrackerProjectNameEl
        .keyup(function() {
            bugTrackerProjectNameDirty = ($(this).val() != "");
        })
        .triggerHandler("keyup");

    bugTrackerUseHostingEl
        .change(function() {
            var checked = this.checked;

            bugTrackerTypeEl[0].disabled = checked;

            forEachField(BUG_TRACKER_FIELDS, true, function(el) {
                el[0].disabled = checked;
            });
        })
        .triggerHandler("change");

    hostingTypeEl
        .change(function() {
            updateFormDisplay("hosting_type", HOSTING_SERVICE_FIELDS);
            updateRepositoryType();

            var hostingType = hostingTypeEl[0].value;

            if (hostingType == "custom" ||
                BUG_TRACKER_FIELDS[hostingType] == undefined) {
                bugTrackerUseHostingEl[0].disabled = true;
                bugTrackerUseHostingEl[0].checked = false;
                bugTrackerUseHostingEl.triggerHandler("change");
            } else {
                bugTrackerUseHostingEl[0].disabled = false;
            }
        })
        .triggerHandler("change");

    $("#id_tool")
        .change(function() {
            updateFormDisplay("tool", TOOLS_FIELDS,
                HOSTING_SERVICE_HIDDEN_FIELDS[hostingTypeEl[0].value]);
        })
        .triggerHandler("change");

    bugTrackerTypeEl
        .change(function() {
            updateFormDisplay("bug_tracker_type", BUG_TRACKER_FIELDS);
        })
        .triggerHandler("change");

    var publicKeyPopup = $("#ssh-public-key-popup");

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

