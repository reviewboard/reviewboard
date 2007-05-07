var dh = YAHOO.ext.DomHelper;
var listJsonView = null;
var reviewRequestTemplate = new YAHOO.ext.Template(
	'<tr>' +
	 "<td class=\"summary\" onclick=\"javascript:window.location=&quot;{url}&quot;\"><a href=\"{url}\">{summary}</a></td>" +
	 '<td>{username}</td>' +
	 '<td class="{ageclass}">{last_updated_relative}</td>' +
	'</tr>'
);

function addNavItem(name, count, level, jsonpath, view, group) {
    if (!group) {
        group = "";
    }

	if (level == 0) {
		levelClass = "main-item";
	} else if (level == 1) {
		levelClass = "sub-item";
	} else {
		levelClass = "sub-sub-item";
	}

	var url = '/dashboard?view=' + view;

    if (group) {
        url += "&group=" + group
    }

	el = dh.append(getEl("dashboard-navbar").dom.tBodies[0], {
		tag: 'tr',
		onclick: "javascript:window.location='" + url + "'; return false;",
		children: [{
			tag: 'td',
			cls: 'summary ' + levelClass,
			children: [{
				tag: 'a',
				href: url,
				html: name
			}]
		}, {
			tag: 'td',
			html: '' + count
		}]
	}, true);

    if (gCurView == view && gCurGroup == group) {
        el.addClass("selected");
    }
}
