var dh = YAHOO.ext.DomHelper;

// State variables
var gCommentSections = {};
var gYourComments = {};

function onEditComplete(field, value, callback) {
	var updateManager = getEl(field).getUpdateManager();
	updateManager.showLoadIndicator = false;
	getEl(field).load('json/' + field + '/', {value: value}, callback);
	showDraftBanner();
}

function registerEditor(field, multiline) {
	var editor = new RB.widgets.InlineEditor({
		el: field,
		multiline: multiline,
		cls: field + '-editor',
		showEditIcon: true
	});

	editor.on('complete',
		function(editor, value) { onEditComplete(field, value); },
		this, true);
}

function registerCommaListEditor(path_prefix, field) {
	var editor = new RB.widgets.InlineCommaListEditor({
		el: field,
		cls: field + '-editor',
		showEditIcon: true,
		useEditIconOnly: true,
		notifyUnchangedCompletion: true
	});

	editor.on('complete',
		function(editor, value) {
			onEditComplete(field, value,
				function(el, success) {
					var list = editor.getList();
					var str = "";

					for (var i = 0; i < list.length; i++) {
						list[i] = list[i].stripTags().strip();
						str += "<a href=\"" + path_prefix + list[i] + "\">";
						str += list[i] + "</a>";

						if (i < list.length - 1) {
							str += ", ";
						}
					}

					getEl(field).dom.innerHTML = str;
				}
			)
		}
	);
}

function disableDraftButtons() {
	getEl('btn-draft-save').dom.setAttribute('disabled', 'true');
	getEl('btn-draft-revert').dom.setAttribute('disabled', 'true');
}

function enableDraftButtons() {
	getEl('btn-draft-save').dom.removeAttribute('disabled');
	getEl('btn-draft-revert').dom.removeAttribute('disabled');
}

var errorID = 0;
function showError(text) {
	var id = 'error' + errorID;
	var closeHandler = "hideError('" + id + "');";

	dh.append(getEl('error').dom, {
		tag: 'div', id: id, children: [
			{tag: 'h1', html: 'Error:'},
			{html: text},
			{tag: 'input', type: 'submit',
			 value: 'Dismiss', onClick: closeHandler}
		]
	});
	errorID += 1;
}

function showServerError(specific) {
	showError(specific +
	          " Please try again later. If this continues to" +
	          " happen, please report it to your administrator");
}

function hideError(error) {
	var node = getEl(error);
	if (node != null) {
		node.remove();
	}
}

function submitDraft() {
	disableDraftButtons();
	YAHOO.util.Connect.asyncRequest('GET', 'draft/save/', {
		success: hideDraftBanner,
		failure: function(response) {
			showServerError('Saving the draft has failed due to a server error.');
			enableDraftButtons();
		}
	});
}

function revertDraft() {
	disableDraftButtons();
	YAHOO.util.Connect.asyncRequest('GET', 'draft/revert/', {
		success: function() { window.location.reload(); },
		failure: function(response) {
			showServerError('Reverting the draft has failed due to a server error.');
			enableDraftButtons();
		}
	});
}

function showDraftBanner() {
	if (getEl('draft') == null) {
		dh.append(getEl('banner').dom, {
			tag: 'div', id: 'draft', children: [
				{tag: 'h1', html: 'This review request is a draft.'},
				{html: ' Be sure to save when finished.'},
				{tag: 'input', type: 'submit', id: 'btn-draft-save',
				 value: 'Save', onClick: 'submitDraft();'},
				{tag: 'input', type: 'submit', id: 'btn-draft-revert',
				 value: 'Revert', onClick: 'revertDraft();'}
			]
		});
	}
}

function hideDraftBanner() {
	var node = getEl('draft') || getEl('discard');

	if (node != null) {
		node.remove();
	}
}

function showDiscardBanner() {
	dh.append(getEl('banner').dom, {
		tag: 'div', id: 'discard', children: [
			{tag: 'h1', html: 'Confirm Discard?'},
			{html:' This cannot be undone.'},
			{tag: 'input', type: 'submit', value: 'Confirm',
			 onClick: 'discardReview();'},
			{tag: 'input', type: 'submit', value: 'Cancel',
			 onClick: 'hideDraftBanner();'}
		]
	});
}

function discardReview() {
	/*
	 * The link that can get us here adds a '#', so it has to be
	 * stripped off.
	 */
	loc = String(window.location);
	window.location = loc.substring(0, loc.length - 1) + 'discard/';
}

function showCommentForm(listid) {
/*
	var list = getEl(listid);
	var item = dh.append(list.dom, {
		tag: "li",
		children: [
			{tag: 'div', 
	var editor = new RB.widgets.InlineEditor({
		el: field,
		multiline: true,
		cls: 'inline-comment-editor',
		showEditIcon: true,
		stripTags: true
	});
*/
}

function registerCommentEditor(id) {
	var editor = new RB.widgets.InlineEditor({
		el: getEl(id),
		multiline: true,
		cls: 'inline-comment-editor',
		stripTags: true,
		showEditIcon: true
	});
}

function registerCommentSection(reviewid, sectionid) {
	if (!gCommentSections[reviewid]) {
		gCommentSections[reviewid] = {};
	}

	gCommentSections[reviewid][sectionid] = {
		comments_list: getEl(sectionid),
		add_comment_button: getEl('add_comment_' + sectionid),
		yourcomment: getEl('yourcomment_' + sectionid)
	};

	console.debug(gCommentSections[reviewid][sectionid].yourcomment)
	if (gCommentSections[reviewid][sectionid].yourcomment) {
		gCommentSections[reviewid][sectionid].add_comment_button.hide();
	}
}
