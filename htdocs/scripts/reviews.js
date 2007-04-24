var dh = YAHOO.ext.DomHelper;
var commentTemplate = null;

// State variables
var gCommentSections = {};
var gYourComments = {};
var gReviews = {};

function getApiPath() {
    return '/api/json/reviewrequests/' + gReviewRequestId;
}

function onEditComplete(field, value, callback) {
    asyncJsonRequest("POST", getApiPath() + '/draft/set/' + field + '/', {
            success: function(rsp) {
                if (callback) {
                    callback(getEl(field), rsp[field]);
                }
                showDraftBanner();
            }.createDelegate(this)
            // TODO: Handle errors
        },
        "value=" + encodeURIComponent(value)
    );
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

function registerCommaListEditor(field, onComplete) {
	var editor = new RB.widgets.InlineCommaListEditor({
		el: field,
		cls: field + '-editor',
		showEditIcon: true,
		useEditIconOnly: true,
		notifyUnchangedCompletion: true
	});

	editor.on('complete', function(editor, value) {
		onEditComplete(field, value, onComplete);
	});
}

function onBugsChanged(el, list) {
	var str = "";

	for (var i = 0; i < list.length; i++) {
		str += "<a href=\"http://bugzilla/show_bug.cgi?id=" + list[i] + "\">";
		str += list[i] + "</a>";

		if (i < list.length - 1) {
			str += ", ";
		}
	}

	el.dom.innerHTML = str;
}

function onTargetPeopleChanged(el, list) {
	var str = "";

	for (var i = 0; i < list.length; i++) {
		str += "<a href=\"" + list[i].url + "\">";
		str += list[i].username + "</a>";

		if (i < list.length - 1) {
			str += ", ";
		}
	}

	el.dom.innerHTML = str;
}

function onTargetGroupsChanged(el, list) {
	var str = "";

	for (var i = 0; i < list.length; i++) {
		str += "<a href=\"" + list[i].url + "\">";
		str += list[i].name + "</a>";

		if (i < list.length - 1) {
			str += ", ";
		}
	}

	el.dom.innerHTML = str;
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
	asyncJsonRequest('POST', getApiPath() + '/draft/save/', {
		success: hideDraftBanner,
		failure: function(errmsg) {
			showServerError('Saving the draft has failed due to a server error:' + errmsg);
			enableDraftButtons();
		}
	});
}

function revertDraft() {
	disableDraftButtons();
	asyncJsonRequest('POST', getApiPath() + '/draft/discard/', {
		success: function() { window.location.reload(); },
		failure: function(errmsg) {
			showServerError('Reverting the draft has failed due to a server error:' + errmsg);
			enableDraftButtons();
		}
	});
}

function showDraftBanner() {
	if (getEl('draft') == null) {
		dh.append(getEl('main-banner').dom, {
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
	dh.append(getEl('main-banner').dom, {
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

function showCommentForm(review_id, section_id) {
	if (commentTemplate == null) {
		commentTemplate = new YAHOO.ext.DomHelper.createTemplate({
			tag: 'li',
			cls: 'reply-comment draft',
			id: "{id}-item",
			children: [{
				tag: 'dl',
				children: [{
					tag: 'dt',
					children: [{
						tag: 'label',
						htmlFor: '{id}',
						children: [{
							tag: 'a',
							href: gUserURL,
							html: gUserFullName
						}]
					}, {
						tag: 'dd',
						children: [{
							tag: 'pre',
							id: '{id}'
						}]
					}]
				}]
			}]
		});
	}

	var list = getEl(section_id);
	var yourcomment_id = "yourcomment_" + section_id + "-draft";
	gYourComments[section_id] = yourcomment_id;

	commentTemplate.append(list.dom, {id: yourcomment_id});
	gCommentSections[section_id].yourcomment = getEl(yourcomment_id);

	var editor = registerCommentEditor(review_id, section_id, yourcomment_id);
	autosetAddCommentVisibility(section_id);

	editor.startEdit();
}

function removeCommentForm(review_id, section_id, yourcomment_id) {
	var item = getEl(yourcomment_id + "-item");
	item.hide(true, .35, item.remove.createDelegate(item))

	gYourComments[section_id] = null;
	gCommentSections[section_id].yourcomment = null;
	autosetAddCommentVisibility(section_id);

	gReviews[review_id].yourCommentCount--;

	if (gReviews[review_id].yourCommentCount == 0) {
		hideReplyDraftBanner(review_id);
	}
}

function registerCommentEditor(review_id, section_id, yourcomment_id) {
	gYourComments[section_id] = yourcomment_id;

	if (!gReviews[review_id]) {
		gReviews[review_id] = { yourCommentCount: 0 };
	}

	gReviews[review_id].yourCommentCount++;

	var editor = new RB.widgets.InlineEditor({
		el: getEl(yourcomment_id),
		multiline: true,
		cls: 'inline-comment-editor',
		stripTags: true,
		showEditIcon: true,
		notifyUnchangedCompletion: true
	});

	var cb = function(editor, value) {
		onReplyEditComplete(value, section_id, yourcomment_id);
	};

	editor.on('complete', cb, this, true);
	editor.on('cancel', cb, this, true);

	return editor;
}

function onReplyEditComplete(value, section_id, yourcomment_id) {
	var review_id = gCommentSections[section_id].review_id;

	var postData =
		"value="     + encodeURIComponent(value) + "&" +
		"id="        + gCommentSections[section_id].id + "&" +
		"type="      + gCommentSections[section_id].type + "&" +
		"review_id=" + review_id

    asyncJsonRequest(
        "POST", getApiPath() + "/reviews/" + review_id + "/replies/draft/", {
		success: function(rsp) {
			if (value.stripTags().strip() == "") {
				removeCommentForm(review_id, section_id, yourcomment_id);
			}
		}.createDelegate(this),

		failure: function(errmsg, rsp) {
			// TODO: Show an error
		}.createDelegate(this)
	}, postData);

	showReplyDraftBanner(review_id);
}

function registerCommentSection(reviewid, section_id, context_id, context_type) {
	gCommentSections[section_id] = {
		comments_list: getEl(section_id),
		add_comment: getEl('add_comment_' + section_id),
		review_id: reviewid,
		id: context_id,
		type: context_type
	};

	if (gYourComments[section_id]) {
		gCommentSections[section_id].yourcomment =
			getEl(gYourComments[section_id]);
		showReplyDraftBanner(reviewid);
	}

	autosetAddCommentVisibility(section_id);
}

function showReplyDraftBanner(review_id) {
	if (getEl(review_id + '-draft') == null) {
		dh.append(getEl(review_id + '-banner').dom, {
			tag: 'div', id: review_id + '-draft', children: [
				{tag: 'h1', html: 'This reply is a draft.'},
				{html: ' Be sure to save when finished.'},
				{tag: 'input', type: 'submit',
				 id: review_id + '-btn-draft-save',
				 value: 'Save',
				 onClick: "submitReplyDraft('" + review_id + "');"},
				{tag: 'input', type: 'submit',
				 id: review_id + '-btn-draft-discard',
				 value: 'Discard',
				 onClick: "discardReplyDraft('" + review_id + "');"}
			]
		});
	}
}

function submitReplyDraft(review_id) {
	disableReplyDraftButtons(review_id);
	var url = getApiPath() + '/reviews/' + review_id + '/replies/draft/save/';
    asyncJsonRequest("POST", url, {
		success: function() { window.location.reload(); },
		failure: function(rsp) {
			showServerError('Saving the reply draft has failed due to a server error.');
			enableReplyDraftButtons(review_id);
		}
	});
}

function discardReplyDraft(review_id) {
	disableReplyDraftButtons(review_id);
	var url = getApiPath() + '/reviews/' + review_id + '/replies/draft/discard/';
    asyncJsonRequest("POST", url, {
		success: function() { window.location.reload(); },
		failure: function(rsp) {
			showServerError('Discarding the reply draft has failed due to a server error.');
			enableReplyDraftButtons(review_id);
		}
	});
}

function disableReplyDraftButtons(review_id) {
	getEl(review_id + '-btn-draft-save').dom.setAttribute('disabled', 'true');
	getEl(review_id + '-btn-draft-discard').dom.setAttribute('disabled', 'true');
}

function enableReplyDraftButtons(review_id) {
	getEl(review_id + '-btn-draft-save').dom.removeAttribute('disabled');
	getEl(review_id + '-btn-draft-discard').dom.removeAttribute('disabled');
}

function hideReplyDraftBanner(review_id) {
	var node = getEl(review_id + '-draft') || getEl(review_id + '-discard');

	if (node != null) {
		node.remove();
	}
}

function autosetAddCommentVisibility(section_id) {
	if (gYourComments[section_id]) {
		gCommentSections[section_id].add_comment.hide(true);
	} else {
		gCommentSections[section_id].add_comment.show(true);
	}
}
