var dh = YAHOO.ext.DomHelper;
var commentTemplate = null;

// Dialogs
var gDeleteReviewRequestDlg = null;
var gDiscardReviewRequestDlg = null;

// State variables
var gCommentSections = {};
var gYourComments = {};
var gReviews = {};
var gEditors = [];
var gPublishing = true;
var gSavedFieldCount = 0;

function getApiPath() {
    return '/api/json/reviewrequests/' + gReviewRequestId;
}

function normalizeURL(url) {
    i = url.indexOf("#");

    if (i != -1) {
        url = url.substring(0, i);
    }

    if (url[url.length - 1] == "/") {
        url = url.substring(0, url.length - 1);
    }

    return url;
}

function onEditComplete(field, value, callback) {
    asyncJsonRequest("POST", getApiPath() + '/draft/set/' + field + '/', {
            success: function(rsp) {
                if (callback) {
                    callback(getEl(field), rsp[field]);
                }
                showDraftBanner();

                if (gPublishing) {
                    gSavedFieldCount++;
                    checkReadyForPublish();
                }
            }.createDelegate(this),

            failure: function(errmsg) {
                /* No way we're publishing now. */
                gPublishing = false;
                showServerError('Saving the draft has failed due to a ' +
                                'server error:' + errmsg);
                enableDraftButtons();
            }.createDelegate(this)
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

    gEditors.push(editor);
}

function registerCommaListEditor(field, onComplete) {
    var editor = new RB.widgets.InlineCommaListEditor({
        el: field,
        cls: field + '-editor',
        autocomplete: false,
        showEditIcon: true,
        useEditIconOnly: true,
        notifyUnchangedCompletion: true
    });

    editor.on('complete', function(editor, value) {
        onEditComplete(field, value, onComplete);
    });

    gEditors.push(editor);
}

function registerAutoCompleteCommaListEditor(field, onComplete, url, columns) {
    var myDataSource = new YAHOO.widget.DS_XHR(url, columns);
    var editor = new RB.widgets.InlineCommaListEditor({
        el: field,
        cls: field + '-editor',
        autocomplete: myDataSource,
        showEditIcon: true,
        useEditIconOnly: true,
        notifyUnchangedCompletion: true
    });

    editor.on('complete', function(editor, value) {
        onEditComplete(field, value, onComplete);
    });

    gEditors.push(editor);
}

function onBugsChanged(el, list) {
    if (gBugTrackerURL == "") {
        el.dom.innerHTML = RB.utils.urlizeList(list);
    } else {
        el.dom.innerHTML = RB.utils.urlizeList(list, function(item) {
            return gBugTrackerURL.replace("%s", item);
        });
    }
}

function onTargetPeopleChanged(el, list) {
    el.dom.innerHTML = RB.utils.urlizeList(list,
        function(item) { return item.url },
        function(item) { return item.username }
    );
}

function onTargetGroupsChanged(el, list) {
    el.dom.innerHTML = RB.utils.urlizeList(list,
        function(item) { return item.url },
        function(item) { return item.name }
    );
}

function disableDraftButtons() {
    getEl('btn-draft-publish').dom.setAttribute('disabled', 'true');
    getEl('btn-draft-discard').dom.setAttribute('disabled', 'true');
}

function enableDraftButtons() {
    getEl('btn-draft-publish').dom.removeAttribute('disabled');
    getEl('btn-draft-discard').dom.removeAttribute('disabled');
}

var errorID = 0;
function showError(text) {
    var id = 'error' + errorID;
    var closeHandler = "hideError('" + id + "');";

    dh.append(getEl('error').dom, {
        tag: 'div',
        cls: 'banner',
        id: id,
        children: [
            {tag: 'h1', html: 'Error: '},
            {html: text},
            {tag: 'input', type: 'submit',
             value: 'Dismiss', onClick: closeHandler}
        ]
    });
    errorID += 1;
}

function showServerError(specific) {
    showError(specific +
              ". Please try again later. If this continues to" +
              " happen, please report it to your administrator");
}

function hideError(error) {
    var node = getEl(error);
    if (node != null) {
        node.remove();
    }
}


/*
 * Publishes the draft to the server.
 */
function publishDraft() {
    /* First save all the fields. */
    gSavedFieldCount = 0;
    gPublishing = true;

    for (var i = 0; i < gEditors.length; i++) {
        if (gEditors[i].editing) {
            gEditors[i].save();
        } else {
            gSavedFieldCount++;
        }
    }

    checkReadyForPublish();
}

/*
 * Checks if we're ready to publish a draft.
 *
 * This compares the saved field count to the number of fields to determine
 * if we've successfully saved all pending fields before we publish.
 */
function checkReadyForPublish() {
    if (gPublishing && gSavedFieldCount == gEditors.length) {
        publishDraftFinal();
    }
}


/*
 * The final step in publishing the draft to the server.
 *
 * Checks all the fields to make sure we have the information we need
 * and then redirects the user to the publish URL.
 */
function publishDraftFinal() {
    var target_groups = document.getElementById("target_groups");
    var target_people = document.getElementById("target_people");
    var summary = document.getElementById("summary");
    var description = document.getElementById("description");

    if (target_groups.innerHTML.strip() == "" &&
        target_people.innerHTML.strip() == "") {
        alert("There must be at least one reviewer before this review " +
              "request can be published.");
    } else if (summary.innerHTML.strip() == "") {
        alert("The draft must have a summary.");
    } else if (description.innerHTML.strip() == "") {
        alert("The draft must have a description.");
    } else {
        window.location = normalizeURL(gReviewRequestPath) + "/publish/";
    }
}


/*
 * Discards the draft.
 */
function discardDraft() {
    disableDraftButtons();
    asyncJsonRequest('POST', getApiPath() + '/draft/discard/', {
        success: function() { window.location.reload(); },
        failure: function(errmsg) {
            showServerError('Reverting the draft has failed due to a server error:' +
                      errmsg);
            enableDraftButtons();
        }
    });
}


/*
 * Displays the draft banner to the user.
 */
function showDraftBanner() {
    getEl('draft-banner').show();
}


/*
 * Hides the draft banner from the user.
 */
function hideDraftBanner() {
    getEl('draft-banner').hide();
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
        dh.append(getEl(review_id + '-banners').dom, {
            tag: 'div',
            cls: 'banner',
            id: review_id + '-draft',
            children: [
                {tag: 'h1', html: 'This reply is a draft.'},
                {html: ' Be sure to publish when finished.'},
                {tag: 'input', type: 'submit',
                 id: review_id + '-btn-draft-publish',
                 value: 'Publish',
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
    getEl(review_id + '-btn-draft-publish').dom.setAttribute('disabled', 'true');
    getEl(review_id + '-btn-draft-discard').dom.setAttribute('disabled', 'true');
}

function enableReplyDraftButtons(review_id) {
    getEl(review_id + '-btn-draft-publish').dom.removeAttribute('disabled');
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


/*
 * Asks the user if they're sure they want to discard the review request.
 * If the user confirms the operation, the review request is discarded.
 */
function discardReviewRequest() {
    if (!gDiscardReviewRequestDlg) {
        gDiscardReviewRequestDlg = new RB.dialogs.MessageDialog({
            title: "Confirm Discard",
            summary: "Are you sure you want to discard this review request?",
            buttons: [{
                text: "Discard",
                cb: onDiscardReviewRequestConfirmed
            }, {
                text: "Cancel",
                is_default: true
            }]
        });
    }

    gDiscardReviewRequestDlg.show(getEl("discard-review-request-link"));
}


/*
 * Asks the user if they're sure they want to delete the review request.
 * If the user confirms the operation, the review request is deleteed.
 */
function deleteReviewRequest() {
    if (!gDeleteReviewRequestDlg) {
        gDeleteReviewRequestDlg = new RB.dialogs.MessageDialog({
            title: "Confirm Deletion",
            summary: "Are you sure you want to delete this review request?",
            description: "This action is irreversible.",
            buttons: [{
                text: "Delete",
                cb: onDeleteReviewRequestConfirmed
            }, {
                text: "Cancel",
                is_default: true
            }]
        });
    }

    gDeleteReviewRequestDlg.show(getEl("delete-review-request-link"));
}

/*
 * Callback function for when the user confirms they want to discard the
 * review request. Performs the discard operation and loads the base
 * Review Board URL.
 */
function onDiscardReviewRequestConfirmed() {
    window.location = normalizeURL(gReviewRequestPath) + "/discard/";
}


/*
 * Callback function for when the user confirms they want to delete the
 * review request. Performs the deletion operation and loads the base
 * Review Board URL.
 */
function onDeleteReviewRequestConfirmed() {
    asyncJsonRequest("POST", getApiPath() + '/delete/', {
        success: function(rsp) {
            window.location = "/"; // XXX Need a better path.
        },
        failure: function(errmsg) {
            showServerError("Deleting the review request has failed " +
                            "due to a server error: " + errmsg);
        }
    });
}

// vim: set et:ts=4:
