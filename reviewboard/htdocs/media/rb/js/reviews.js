
// State variables
var gCommentDlg = null;
var gEditCount = 0;
var gPublishing = false;
var gPendingSaveCount = 0;
var gPendingDiffFragments = {};
var gReviewBanner = $("#review-banner");
var gDraftBanner = $("#draft-banner");
var gDraftBannerButtons = $("input", gDraftBanner);
var gFileAttachmentComments = {};
var gReviewRequest = new RB.ReviewRequest(gReviewRequestId,
                                          gReviewRequestSitePrefix,
                                          gReviewRequestPath);


/*
 * "complete" signal handlers for various fields, designed to do
 * post-processing of the values for display.
 */
var gEditorCompleteHandlers = {
    'bugs_closed': function(data) {
        if (gBugTrackerURL == "") {
            return data.join(", ");
        } else {
            return urlizeList(data, function(item) {
                return gBugTrackerURL.replace("%s", item);
            });
        }
    },
    'target_groups': function(data) {
        return urlizeList(data,
            function(item) { return item.url; },
            function(item) { return item.name; }
        );
    },
    'target_people': function(data) {
        return $(urlizeList(data,
                            function(item) { return item.url; },
                            function(item) { return item.username; }))
            .addClass("user")
            .user_infobox();
    },
    'description': linkifyText,
    'testing_done': linkifyText
};


/*
 * gCommentIssueManager takes care of setting the state of a particular
 * comment issue, and also takes care of notifying callbacks whenever
 * the state is successfully changed.
 */
var gCommentIssueManager = new function() {
    var callbacks = {};
    var comments = {};

    /*
     * setCommentState - set the state of comment issue
     * @param review_id the id for the review that the comment belongs to
     * @param comment_id the id of the comment with the issue
     * @param comment_type the type of comment, either "diff_comments",
     *                     "screenshot_comments", or "file_attachment_comments".
     * @param state the state to set the comment issue to - either
     *              "open", "resolved", or "dropped"
     */
    this.setCommentState = function(review_id, comment_id,
                                    comment_type, state) {
        var comment = getComment(review_id, comment_id, comment_type);
        requestState(comment, state);
    };

    /*
     * registerCallback - allows clients to register callbacks to be
     * notified when a particular comment state is updated.
     * @param comment_id the id of the comment to be notified about
     * @param callback a function of the form:
     *                 function(issue_state) {}
     */
    this.registerCallback = function(comment_id, callback) {
        if (!callbacks[comment_id]) {
            callbacks[comment_id] = [];
        }

        callbacks[comment_id].push(callback);
    };

    /*
     * A helper function to either generate the appropriate
     * comment object based on comment_type, or to grab the
     * comment from a cache if it's been generated before.
     */
    function getComment(review_id, comment_id, comment_type) {
        if (comments[comment_id]) {
            return comments[comment_id];
        }

        var comment = null;

        if (comment_type === "diff_comments") {
            comment = gReviewRequest
                .createReview(review_id)
                .createDiffComment(comment_id);
        } else if (comment_type === "screenshot_comments") {
            comment = gReviewRequest
                .createReview(review_id)
                .createScreenshotComment(comment_id);
        } else if (comment_type === "file_attachment_comments") {
            comment = gReviewRequest
                .createReview(review_id)
                .createFileAttachmentComment(comment_id);
        } else {
            console.log("getComment received unexpected context type '%s'",
                        comment_type);
        }

        comments[comment_id] = comment;
        return comment;
    }

    // Helper function to set the state of a comment
    function requestState(comment, state) {
        comment.ready(function() {
            comment.issue_status = state;
            comment.save({
                success: function(rsp) {
                    notifyCallbacks(comment.id, comment.issue_status);

                    /*
                     * We don't want the current user to receive the
                     * notification that the review request has been
                     * updated, since they themselves updated the
                     * issue status.
                     */
                    if (rsp.last_activity_time) {
                        gReviewRequest.markUpdated(rsp.last_activity_time);
                    }
                }
            });
        });
    }

    /*
     * Helper function that notifies all callbacks registered for
     * a particular comment
     */
    function notifyCallbacks(comment_id, issue_status) {
        for (var i = 0; i < callbacks[comment_id].length; i++) {
            callbacks[comment_id][i](issue_status);
        }
    }
}();


/*
 * Converts an array of items to a list of hyperlinks.
 *
 * By default, this will use the item as the URL and as the hyperlink text.
 * By overriding urlFunc and textFunc, the URL and text can be customized.
 *
 * @param {array}    list            The list of items.
 * @param {function} urlFunc         A function to return the URL for an item
 *                                   in the list.
 * @param {function} textFunc        A function to return the text for an item
 *                                   in the list.
 * @param {function} postProcessFunc Post-process generated elements in the
                                     list.
 *
 * @return A string containing the HTML markup for the list of hyperlinks.
 */
function urlizeList(list, urlFunc, textFunc, postProcessFunc) {
    var str = "";

    for (var i = 0; i < list.length; i++) {
        var item = list[i];
        str += '<a href="';
        str += (urlFunc ? urlFunc(item) : item);
        str += '">';
        str += (textFunc ? textFunc(item) : item);
        str += '</a>';

        if (i < list.length - 1) {
            str += ", ";
        }
    }

    return str;
}


/*
 * Linkifies a block of text, turning URLs, /r/#/ paths, nad bug numbers
 * into clickable links.
 *
 * @param {string} text  The text to linkify.
 *
 * @returns {string} The resulting HTML.
 */
function linkifyText(text) {
    text = text.htmlEncode();

    /* Linkify all URLs. */
    text = text.replace(
        /\b([a-z]+:\/\/[\-A-Za-z0-9+&@#\/%?=~_()|!:,.;]*([\-A-Za-z0-9+@#\/%=~_();|]|))/g,
        function(url) {
            /*
             * We might catch an entity at the end of the URL. This is hard
             * to avoid, since we can't rely on advanced RegExp techniques
             * in all browsers. So, we'll now search for it and prevent it
             * from being part of the URL if it exists. However, a URL with 
             * an open bracket will not have its close bracket removed. This
             * was a modification to the original bug fix.
             *
             * See bug 1069.
             */

            var extra = '',
                parts = url.match(/^(.*)(&[a-z]+;|\))/),
                openParen = url.match(/.*\(.*/);

            if (parts != null && openParen == null ) {
                /* We caught an entity. Set it free. */
                url = parts[1];
                extra = parts[2];
            }

            return '<a href="' + url + '">' + url + '</a>' + extra;
        });


    /* Linkify /r/#/ review request numbers */
    text = text.replace(
        /(^|\s|&lt;)\/(r\/\d+(\/[\-A-Za-z0-9+&@#\/%?=~_()|!:,.;]*[\-A-Za-z0-9+&@#\/%=~_()|])?)/g,
        '$1<a href="' + SITE_ROOT + '$2">/$2</a>');

    /* Bug numbers */
    if (gBugTrackerURL != "") {
        text = text.replace(/\b(bug|issue) (#([^.\s]+)|#?(\d+))/gi,
            function(text, m2, m3, bugnum1, bugnum2) {
                /*
                 * The bug number can appear in either of those groups,
                 * depending on how this was typed, so try both.
                 */
                var bugnum = bugnum1 || bugnum2;

                return '<a href="' +
                       gBugTrackerURL.replace("%s", bugnum) +
                       '">' + text + '</a>';
            });
    }

    return text;
}


/*
 * Sets a field in the draft.
 *
 * If we're in the process of publishing, this will check if we have saved
 * all fields before publishing the draft.
 *
 * @param {string} field  The field name.
 * @param {string} value  The field value.
 */
function setDraftField(field, value) {
    gReviewRequest.setDraftField({
        field: field,
        value: value,
        buttons: gDraftBannerButtons,
        success: function(rsp) {
            /* Checking if invalid user or group was entered. */
            if (rsp.stat == "fail" && rsp.fields) {

                $('#review-request-warning')
                    .delay(6000)
                    .fadeOut(400, function() {
                        $(this).hide();
                });

                /* Wrap each term in quotes or a leading 'and'. */
                $.each(rsp.fields[field], function(key, value) {
                    var size = rsp.fields[field].length;

                    if (key == size - 1 && size > 1) {
                      rsp.fields[field][key] = "and '" + value + "'";
                    } else {
                      rsp.fields[field][key] = "'" + value + "'";
                    }
                });

                var message = rsp.fields[field].join(", ");

                if (rsp.fields[field].length == 1) {
                    if (field == "target_groups") {
                        message = "Group " + message + " does not exist.";
                    } else {
                        message = "User " + message + " does not exist.";
                    }
                } else {
                    if (field == "target_groups") {
                        message = "Groups " + message + " do not exist.";
                    } else {
                        message = "Users " + message + " do not exist.";
                    }
                }

                $("#review-request-warning").html(message).show();
            }

            var func = gEditorCompleteHandlers[field];

            if ($.isFunction(func)) {
                $("#" + field).html(func(rsp['draft'][field]));
            }

            gDraftBanner.show();

            if (gPublishing) {
                gPendingSaveCount--;

                if (gPendingSaveCount == 0) {
                    publishDraft();
                }
            }
        },
        error: function() {
            gPublishing = false;
        }
    });
}


/*
 * An autocomplete() wrapper that converts our autocomplete data into the
 * format expected by jQuery.ui.autocomplete. It also adds some additional
 * explanatory text to the bottom of the autocomplete list.
 *
 * options has the following fields:
 *
 *    fieldName   - The field name ("groups" or "people").
 *    nameKey     - The key containing the name in the result data.
 *    descKey     - The key containing the description in the result
 *                  data. This is optional.
 *    extraParams - Extra parameters to send in the query. This is optional.
 *
 * @param {object} options    The options, as listed above.
 *
 * @return {jQuery} This jQuery set.
 */
$.fn.reviewsAutoComplete = function(options) {
    return this.each(function() {
        $(this)
            .autocomplete({
                formatItem: function(data) {
                    var s = data[options.nameKey],
                        desc;

                    if (options.descKey) {
                        desc = $('<div/>').text(data[options.descKey]).html();
                        s += " <span>(" + desc + ")</span>";
                    }

                    return s;
                },
                matchCase: false,
                multiple: true,
                parse: function(data) {
                    var jsonData = eval("(" + data + ")");
                    var items = jsonData[options.fieldName];
                    var parsed = [];

                    for (var i = 0; i < items.length; i++) {
                        var value = items[i];

                        parsed.push({
                            data: value,
                            value: value[options.nameKey],
                            result: value[options.nameKey]
                        });
                    }

                    return parsed;
                },
                url: SITE_ROOT + gReviewRequestSitePrefix + "api/" + options.fieldName + "/",
                extraParams: options.extraParams
            })
            .bind("autocompleteshow", function() {
                /*
                 * Add the footer to the bottom of the results pane the
                 * first time it's created.
                 *
                 * Note that we may have multiple .ui-autocomplete-results
                 * elements, and we don't necessarily know which is tied to
                 * this. So, we'll look for all instances that don't contain
                 * a footer.
                 */
                var resultsPane = $(".ui-autocomplete-results:not(" +
                                    ":has(.ui-autocomplete-footer))");

                if (resultsPane.length > 0) {
                    $("<div/>")
                        .addClass("ui-autocomplete-footer")
                        .text("Press Tab to auto-complete.")
                        .appendTo(resultsPane);
                }
            });
    });
};


/*
 * Publishes the draft to the server. This assumes all fields have been
 * saved.
 *
 * Checks all the fields to make sure we have the information we need
 * and then redirects the user to the publish URL.
 */
function publishDraft() {
    if ($.trim($("#target_groups").html()) == "" &&
        $.trim($("#target_people").html()) == "") {
        alert("There must be at least one reviewer or group " +
        "before this review request can be published.");
    } else if ($.trim($("#summary").html()) == "") {
        alert("The draft must have a summary.");
    } else if ($.trim($("#description").html()) == "") {
        alert("The draft must have a description.");
    } else {
        gReviewRequest.publish({
            buttons: gDraftBannerButtons
        });
    }
}


/*
 * Handles a comment section in a review.
 *
 * This will handle the "Add Comment" link and the draft banners for the
 * review.
 *
 * @param {string} review_id     The review ID.
 * @param {string} context_id    The comment section context ID.
 * @param {string} context_type  The comment section context type.
 *
 * @return {jQuery} This jQuery.
 */
$.fn.commentSection = function(review_id, context_id, context_type) {
    var self = $(this);

    var review = gReviewRequest.createReview(review_id);
    var review_reply = review.createReply();

    var sectionId = context_id;
    var reviewEl = $("#review" + review_id);
    var commentsList = $(".reply-comments", self)
    var bannersEl = $(".banners", reviewEl);
    var bannerButtonsEl = $("input", bannersEl)

    var addCommentLink = $(".add_comment_link", self)
        .click(function() {
            createNewCommentForm();
            return false;
        });

    var yourcomments = $("pre[id^=yourcomment_]", self);

    if (yourcomments.length > 0) {
        createCommentEditor(yourcomments);
        showReplyDraftBanner(review_id);
        addCommentLink.hide();
    }

    /*
     * Creates a new comment form in response to the "Add Comment" link.
     */
    function createNewCommentForm() {
        var yourcomment_id = "yourcomment_" + review_id + "_" +
                             context_type;
        if (sectionId) {
            yourcomment_id += "_" + sectionId;
        }

        yourcomment_id += "-draft";

        var yourcomment = $("<li/>")
            .addClass("reply-comment draft editor")
            .attr("id", yourcomment_id + "-item")
            .append($("<dl/>")
                .append($("<dt/>")
                    .append($("<label/>")
                        .attr("for", yourcomment_id)
                        .append($("<a/>")
                            .attr("href", gUserURL)
                            .html(gUserFullName)
                        )
                    )
                    .append('<dd><pre id="' + yourcomment_id + '"/></dd>')
                )
            )
            .appendTo(commentsList);

        var yourcommentEl = $("#" + yourcomment_id);
        createCommentEditor(yourcommentEl);
        yourcommentEl
            .inlineEditor("startEdit")
            .bind("cancel", function(el, initialValue) {
                if (initialValue == "") {
                    yourcomment.remove();
                }
            });

        addCommentLink.hide();
    }

    /*
     * Registers an inline editor for the comment form, handling setting the
     * comment on the server.
     *
     * @param {jQuery} els  The elements to create editors for.
     *
     * @return {jQuery} The provided elements.
     */
    function createCommentEditor(els) {
        return els.each(function() {
            var self = $(this);

            self
                .inlineEditor({
                    cls: "inline-comment-editor",
                    editIconPath: MEDIA_URL + "rb/images/edit.png?" +
                                  MEDIA_SERIAL,
                    notifyUnchangedCompletion: true,
                    multiline: true
                })
                .bind("beginEdit", function() {
                    gEditCount++;
                })
                .bind("complete", function(e, value) {
                    gEditCount--;

                    self.html(linkifyText(self.text()));

                    if (context_type == "body_top" ||
                        context_type == "body_bottom") {
                        review_reply[context_type] = value;
                        obj = review_reply;
                    } else if (context_type === "diff_comments") {
                        obj = new RB.DiffCommentReply(review_reply, null,
                                                      context_id);
                        obj.setText(value);
                    } else if (context_type === "screenshot_comments") {
                        obj = new RB.ScreenshotCommentReply(review_reply, null,
                                                            context_id);
                        obj.setText(value);
                    } else if (context_type === "file_attachment_comments") {
                        obj = new RB.FileAttachmentCommentReply(
                            review_reply, null, context_id);
                        obj.setText(value);
                    } else {
                        /* Shouldn't be reached. */
                        console.log("createCommentEditor received unexpected " +
                                    "context type '%s'",
                                    context_type);
                        return;
                    }

                    obj.save({
                        buttons: bannerButtonsEl,
                        success: function() {
                            removeCommentFormIfEmpty(self);
                            showReplyDraftBanner(review_id);
                        }
                    });
                })
                .bind("cancel", function(e) {
                    gEditCount--;
                    addCommentLink.fadeIn();
                    removeCommentFormIfEmpty(self);
                });
        });
    }

    /*
     * Removes a comment form if the contents are empty.
     *
     * @param {jQuery} editorEl  The inline editor element.
     */
    function removeCommentFormIfEmpty(editorEl) {
        var value = editorEl.inlineEditor("value");

        if (value.stripTags().strip() != "") {
            return;
        }

        $("#" + editorEl[0].id + "-item").hide("slow", function() {
            $(this).remove();

            if ($(".inline-comment-editor", reviewEl).length == 0) {
                bannersEl.children().remove();
            }

            addCommentLink.fadeIn();

            /* Find out if we need to discard this. */
            review_reply.discardIfEmpty({
                buttons: bannerButtonsEl
            });
        });
    }

    /*
     * Shows the reply draft banner on the review.
     *
     * @param {string} review_id  The review object's ID.
     */
    function showReplyDraftBanner(review_id) {
        if (bannersEl.children().length == 0) {
            bannersEl.append($.replyDraftBanner(review_reply,
                                                bannerButtonsEl));
        }
    }
};


/* Handles a comment issue in either the review details page, or the
 * inline comment viewer.
 * @param review_id the id of the review that the comment belongs to
 * @param comment_id the id of the comment with the issue
 * @param comment_type dictates the type of comment - either
 *                     "diff_comments", "screenshot_comments" or
 *                     "file_attachment_comments".
 * @param issue_status the initial status of the comment - either
 *                     "open", "resolved" or "dropped"
 * @param interactive true if the user should be shown buttons to
 *                    manipulate the comment issue - otherwise false.
 */
$.fn.commentIssue = function(review_id, comment_id, comment_type,
                             issue_status, interactive) {
    var self = this;
    var OPEN = 'open';
    var RESOLVED = 'resolved';
    var DROPPED = 'dropped';

    var issue_reopen_button = $(".issue-button.reopen", this);
    var issue_resolve_button = $(".issue-button.resolve", this);
    var issue_drop_button = $(".issue-button.drop", this);
    self.review_id = review_id;
    self.comment_id = comment_id;
    self.comment_type = comment_type;
    self.issue_status = issue_status;
    self.interactive = interactive;

    function disableButtons() {
        issue_reopen_button.attr("disabled", true);
        issue_resolve_button.attr("disabled", true);
        issue_drop_button.attr("disabled", true);
    }

    function enableButtons() {
        issue_reopen_button.attr("disabled", false);
        issue_resolve_button.attr("disabled", false);
        issue_drop_button.attr("disabled", false);
    }

    function enterState(state) {
        disableButtons();
        gCommentIssueManager.setCommentState(self.review_id, self.comment_id,
                                             self.comment_type, state);
    }

    issue_reopen_button.click(function() {
        enterState(OPEN);
    });

    issue_resolve_button.click(function() {
        enterState(RESOLVED);
    });

    issue_drop_button.click(function() {
        enterState(DROPPED);
    });

    self.enter_state = function(state) {
        self.state = self.STATES[state];
        self.state.enter();
        if (self.interactive) {
            self.state.showButtons();
            enableButtons();
        }
    }

    var open_state = {
        enter: function() {
            $(".issue-button.reopen", self).hide();
            $(".issue-state", self)
                .removeClass("dropped")
                .removeClass("resolved")
                .addClass("open");
            $(".issue-message", self)
                .text("An issue was opened.");
        },
        showButtons: function() {
            $(".issue-button.drop", self).show();
            $(".issue-button.resolve", self).show();
        }
    }

    var resolved_state = {
        enter: function() {
            $(".issue-button.resolve", self).hide();
            $(".issue-button.drop", self).hide();
            $(".issue-state", self)
                .removeClass("dropped")
                .removeClass("open")
                .addClass("resolved");
            $(".issue-message", self)
                .text("The issue has been resolved.");
        },
        showButtons: function() {
            $(".issue-button.reopen", self).show();
        }
    }

    var dropped_state = {
        enter: function() {
            $(".issue-button.resolve", self).hide();
            $(".issue-button.drop", self).hide();
            $(".issue-state", self)
                .removeClass("open")
                .removeClass("resolved")
                .addClass("dropped");
            $(".issue-message", self)
                .text("The issue has been dropped.");
        },
        showButtons: function() {
            $(".issue-button.reopen", self).show();
        }
    }

    self.STATES = {};
    self.STATES[OPEN] = open_state;
    self.STATES[RESOLVED] = resolved_state;
    self.STATES[DROPPED] = dropped_state;

    // Set the comment to the initial state
    self.enter_state(self.issue_status);

    // Register to watch updates on the comment issue state
    gCommentIssueManager
        .registerCallback(self.comment_id, self.enter_state);

    return self;
}



/*
 * Wraps an inline comment so that they can display issue
 * information.
 */
$.fn.issueIndicator = function() {
    var issue_indicator = $('<div/>')
        .addClass('issue-state')
        .appendTo(this);

    var message = $('<span/>')
        .addClass('issue-message')
        .appendTo(issue_indicator);

    return this;
}


/*
 * Wraps an inline comment so that it displays buttons
 * for setting the state of a comment issue.
 */
$.fn.issueButtons = function() {
    var issue_indicator = $(".issue-state", this);

    var buttons = $('<div class="buttons"/>')
        .addClass('buttons')
        .appendTo(issue_indicator);

    var resolve_string = "Fixed";
    var drop_string = "Drop";
    var reopen_string = "Re-open";

    var button_string = '<input type="button" class="issue-button resolve"'
                      + 'value="' + resolve_string + '"/>'
                      + '<input type="button" class="issue-button drop"'
                      + 'value="' + drop_string + '"/>'
                      + '<input type="button" class="issue-button reopen"'
                      + 'value="' + reopen_string + '"/>';

    buttons.append(button_string);

    return this;
}


/*
 * Creates a floating reply banner. The banner will stay in view while the
 * parent review is visible on screen.
 */
$.replyDraftBanner = function(review_reply, bannerButtonsEl) {
    var banner = $("<div/>")
        .addClass("banner")
        .append("<h1>This reply is a draft</h1>")
        .append(" Be sure to publish when finished.")
        .append($('<input type="button"/>')
            .val("Publish")
            .click(function() {
                review_reply.publish({
                    buttons: bannerButtonsEl,
                    success: function() {
                        window.location = gReviewRequestPath;
                    }
                });
            })
        )
        .append($('<input type="button"/>')
            .val("Discard")
            .click(function() {
                review_reply.discard({
                    buttons: bannerButtonsEl,
                    success: function() {
                        window.location = gReviewRequestPath;
                    }
                });
            })
        )
        .floatReplyDraftBanner();

    return banner;
}

/*
 * Floats a reply draft banner. This ensures it's always visible on screen
 * when the review is visible.
 */
$.fn.floatReplyDraftBanner = function() {
    return $(this).each(function() {
        var self = $(this);
        var floatSpacer = null;
        var container = null;

        $(window).scroll(updateFloatPosition);
        $(window).resize(updateSize);
        updateFloatPosition();

        function updateSize() {
            if (floatSpacer != null) {
                floatSpacer.height(self.height() +
                                   self.getExtents("bpm", "tb"));
                self.width(floatSpacer.parent().width() -
                           self.getExtents("bpm", "lr"));
            }
        }

        function updateFloatPosition() {
            if (self.parent().length == 0) {
                return;
            }

            /*
             * Something about the below causes the "Publish" button to never
             * show up on IE8. Turn it into a fixed box on IE.
             */
            if ($.browser.msie) {
                return;
            }

            if (floatSpacer == null) {
                floatSpacer = self.wrap($("<div/>")).parent();
                updateSize();
            }

            if (container == null) {
                container = self.closest('.review');
            }

            var containerTop = container.offset().top;
            var windowTop = $(window).scrollTop();
            var topOffset = floatSpacer.offset().top - windowTop;
            var outerHeight = self.outerHeight();

            if (!container.hasClass("collapsed") &&
                topOffset < 0 &&
                containerTop < windowTop &&
                windowTop < (containerTop + container.outerHeight() -
                             outerHeight)) {
                self.css({
                    top: 0,
                    position: "fixed"
                });

                updateSize();
            } else {
                self.css({
                    top: null,
                    position: null
                });
            }
        }
    });
}


/*
 * Creates the comment detail dialog for lines in a diff. This handles the
 * maintenance of comment blocks and shows existing comments on a block.
 *
 * @return {jQuery} This jQuery.
 */
$.fn.commentDlg = function() {
    var DIALOG_TOTAL_HEIGHT = 250;
    var SLIDE_DISTANCE = 10;
    var COMMENTS_BOX_WIDTH = 280;
    var FORM_BOX_WIDTH = 380;
    var self = this;

    /* State */
    var comment = null;
    var textFieldWidthDiff = 0;
    var textFieldHeightDiff = 0;
    var dirty = false;
    var ignoreKeyUp = false;

    /* Page elements */
    var draftForm    = $("#draft-form", this);
    var commentsPane = $("#review_comments", this);
    var commentsList = $("#review_comment_list", this);
    var actionField  = $("#comment_action", draftForm);
    var buttons      = $(".buttons", draftForm);
    var statusField  = $(".status", draftForm);
    var issueOptions = $("#comment-issue-options", draftForm);

    var issueField = $("#comment_issue", draftForm)
        .click(function() {
            saveButton.attr("disabled", textField.val() == "");
            self.setDirty(true);
        });
    var cancelButton = $("#comment_cancel", draftForm)
        .click(function() {
            comment.deleteIfEmpty();
            self.close();
        });
    var deleteButton = $("#comment_delete", this)
        .click(function() {
            comment.deleteComment();
            self.close();
        });
    var saveButton = $("#comment_save", this)
        .click(function() {
            comment.setText(textField.val());
            comment.issue_opened = issueField[0].checked;
            comment.save();
            self.close();
        });

    var textField = $("#comment_text", draftForm)
        .keydown(function(e) { e.stopPropagation(); })
        .keypress(function(e) {
            e.stopPropagation();

            switch (e.which) {
                case 10:
                case $.ui.keyCode.ENTER:
                    /* Enter */
                    if (e.ctrlKey) {
                        ignoreKeyUp = true;
                        saveButton.click();
                    }
                    break;

                case $.ui.keyCode.ESCAPE:
                    /* Escape */
                    ignoreKeyUp = true;
                    cancelButton.click();
                    break;

                case 73:
                case 105:
                    /* I */
                    if (e.altKey) {
                      issueField.click();
                      ignoreKeyUp = true;
                    }

                    break;

                default:
                    ignoreKeyUp = false;
                    break;
            }
        })
        .keyup(function(e) {
            /*
             * We check if we want to ignore this event. The state from
             * some shortcuts (control-enter) may not be settled, and we may
             * end up setting this to dirty, causing page leave confirmations.
             */
            if (!ignoreKeyUp) {
                self.setDirty(dirty || comment.text != textField.val());
                saveButton.attr("disabled", textField.val() == "");
                e.stopPropagation();
            }
        });

    this
        .css("position", "absolute")
        .mousedown(function(evt) {
            /*
             * Prevent this from reaching the selection area, which will
             * swallow the default action for the mouse down.
             */
            evt.stopPropagation();
        })
        .proxyTouchEvents();

    if (!$.browser.msie || $.browser.version >= 9) {
        /*
         * resizable is pretty broken in IE 6/7.
         */
        var grip = $("<img/>")
            .addClass("ui-resizable-handle ui-resizable-grip")
            .attr("src", MEDIA_URL + "rb/images/resize-grip.png?" +
                         MEDIA_SERIAL)
            .insertAfter(buttons)
            .proxyTouchEvents();

        this.resizable({
            handles: $.browser.mobileSafari ? "grip,se"
                                            : "grip,n,e,s,w,se,sw,ne,nw",
            transparent: true,
            resize: function() { self.handleResize(); }
        });

        var startOffset = null;
        var baseWidth = null;
        var baseHeight = null;

        /*
         * Enable resizing through a grip motion on a touchpad.
         */
        $([this[0], textField[0]])
            .bind("gesturestart", function(evt) {
                startOffset = self.offset();
                startWidth = self.width();
                startHeight = self.height();
            })
            .bind("gesturechange", function(evt) {
                if (event.scale == 0) {
                    return false;
                }

                var newWidth = startWidth * event.scale;
                var newHeight = startHeight * event.scale;

                self
                    .width(newWidth)
                    .height(newHeight)
                    .move(startOffset.left - (newWidth - startWidth) / 2,
                          startOffset.top - (newHeight - startHeight) / 2);
                self.handleResize();

                return false;
            });

        /* Reset the opacity, which resizable() changes. */
        grip.css("opacity", 100);
    }

    if (!$.browser.msie || $.browser.version >= 7) {
        /*
         * draggable works in IE7 and up, but not IE6.
         */
        this.draggable({
            handle: $(".title", this).css("cursor", "move")
        });
    }

    if (!gUserAuthenticated) {
        textField.attr("disabled", true);
        saveButton.attr("disabled", true);
    }

    /*
     * Sets the dirty state of the comment dialog.
     *
     * @return {jQuery} This jQuery.
     */
    this.setDirty = function(newDirty) {
        if (newDirty != dirty) {
            dirty = newDirty;

            if (dirty) {
                gEditCount++;
                statusField.html("This comment has unsaved changes.");
            } else {
                gEditCount--;
                statusField.empty();
            }

            if (this.is(":visible")) {
                this.handleResize();
            }
        }

        return this;
    };

    /*
     * Opens the comment dialog and focuses the text field.
     *
     * @return {jQuery} This jQuery.
     */
    this.open = function(fromEl) {
        this
            .css({
                top: parseInt(this.css("top")) - SLIDE_DISTANCE,
                opacity: 0
            })
            .show()
            .handleResize()
            .animate({
                top: "+=" + SLIDE_DISTANCE + "px",
                opacity: 1
            }, 350, "swing", function() {
                self.scrollIntoView();
            })
            .setDirty(false);

        textField.focus();

        return this;
    }

    /*
     * Closes the comment dialog, discarding the comment block if empty.
     *
     * @return {jQuery} This jQuery.
     */
    this.close = function() {
        if (self.is(":visible")) {
            textField.val("");
            issueField[0].checked = false;

            self
                .setDirty(false)
                .animate({
                    top: "-=" + SLIDE_DISTANCE + "px",
                    opacity: 0
                }, 350, "swing", function() {
                    self.hide();
                    self.comment = null;
                    self.trigger("close");
                });
        } else {
            self.trigger("close");
        }

        return this;
    }

    /*
     * Sets the list of existing comments to show.
     *
     * @param {array} comments    The array of comments to show.
     * @param {string} replyType  The reply type for the comments listed.
     *
     * @return {jQuery} This jQuery.
     */
    this.setCommentsList = function(comments, replyType) {
        commentsList.empty();

        /*
         * Store the offsets of the text field so we can easily set
         * them relative to the dialog size when resizing.
         */
        commentsPane.hide();

        var showComments = false;

        if (comments.length > 0) {
            var odd = true;

            $(comments).each(function(i) {
                var item = $("<li/>")
                    .addClass(odd ? "odd" : "even");
                var header = $("<h2/>").appendTo(item).html(this.user.name);
                var actions = $('<span class="actions"/>')
                    .appendTo(header);

                $('<a href="' + this.url + '">View</a>').appendTo(actions);
                $('<a href="' + gReviewRequestPath +
                  '?reply_id=' + this.comment_id +
                  '&reply_type=' + replyType + '">Reply</a>')
                    .appendTo(actions);
                $("<pre/>").appendTo(item).text(this.text);

                if (this.issue_opened) {
                    var interactive = window['gEditable'];
                    var issue = $('<div/>')
                        .issueIndicator();

                    if (interactive) {
                        issue.issueButtons();
                    }

                    issue
                        .commentIssue(this.review_id, this.comment_id,
                                      replyType, this.issue_status, interactive)
                        .appendTo(item);

                    var self = this;

                    gCommentIssueManager.registerCallback(this.comment_id,
                        function(issue_status) {
                            self.issue_status = issue_status;
                        }
                    );
                }

                item.appendTo(commentsList);

                showComments = true;

                odd = !odd;
            });
        }

        commentsPane.setVisible(showComments);

        /* Do this here so that calculations can be done before open() */
        var width = FORM_BOX_WIDTH;

        if (showComments) {
            width += COMMENTS_BOX_WIDTH;
        }

        /* Don't let the text field bump up the size we set below. */
        textField
            .width(10)
            .height(10);

        self
            .width(width)
            .height(DIALOG_TOTAL_HEIGHT);

        return this;
    }

    /*
     * Sets the draft comment to modify. This will reset the default state of
     * the comment dialog.
     *
     * @param {RB.Comment} newComment The new draft comment to set.
     *
     * @return {jQuery} This jQuery.
     */
    this.setDraftComment = function(newComment) {
        if (comment && comment != newComment) {
            comment.deleteIfEmpty();
        }

        comment = newComment;

        comment.ready(function() {
            textField.val(comment.text);
            issueField[0].checked = comment.issue_opened;

            self.setDirty(false);

            /* Set the initial button states */
            deleteButton.setVisible(comment.loaded);
        });

        saveButton.attr("disabled", true);

        /* Clear the status field. */
        statusField.empty();

        return this;
    }

    /*
     * Handles the resize of the comment dialog. This will lay out the
     * elements in the dialog appropriately.
     */
    this.handleResize = function() {
        var width = self.width();
        var height = self.height();
        var formWidth = width - draftForm.getExtents("bp", "lr");
        var boxHeight = height;
        var commentsWidth = 0;

        if (commentsPane.is(":visible")) {
            commentsPane
                .width(COMMENTS_BOX_WIDTH - commentsPane.getExtents("bp", "lr"))
                .height(boxHeight - commentsPane.getExtents("bp", "tb"))
                .move(0, 0, "absolute");

            commentsList.height(commentsPane.height() -
                                commentsList.position().top -
                                commentsList.getExtents("bmp", "b"));

            commentsWidth = commentsPane.outerWidth(true);
            formWidth -= commentsWidth;
        }

        draftForm
            .width(formWidth)
            .height(boxHeight - draftForm.getExtents("bp", "tb"))
            .move(commentsWidth, 0, "absolute");

        var textFieldPos = textField.position();
        textField
            .width(draftForm.width() - textFieldPos.left -
                   textField.getExtents("bmp", "r"))
            .height(draftForm.height() - textFieldPos.top -
                    buttons.outerHeight(true) -
                    statusField.height() -
                    issueOptions.height() -
                    textField.getExtents("bmp", "b"));

        return this;
    }

    return this;
};


/*
 * Creates a review form for modifying a new review.
 *
 * This provides editing capabilities for creating or modifying a new
 * review. The list of comments are retrieved from the server, providing
 * context for the comments.
 *
 * @param {RB.Review} review  The review to create or modify.
 *
 * @return {jQuery} The new review form element.
 */
$.reviewForm = function(review) {
    rbApiCall({
        type: "GET",
        dataType: "html",
        data: {},
        url: gReviewRequestPath + "reviews/draft/inline-form/",
        success: function(html) {
            createForm(html);
        }
    });

    var dlg;
    var buttons;

    /*
     * Creates the actual review form. This is called once we have
     * the HTML for the form from the server.
     *
     * @param {string} formHTML  The HTML content for the form.
     */
    function createForm(formHTML) {
        gEditCount++;

        dlg = $("<div/>")
            .attr("id", "review-form")
            .appendTo("body") // Needed for scripts embedded in the HTML
            .html(formHTML)
            .modalBox({
                title: "Review for: " + gReviewRequestSummary,
                stretchX: true,
                stretchY: true,
                buttons: [
                    $('<input type="button"/>')
                        .val("Publish Review")
                        .click(function(e) {
                            saveReview(true);
                            return false;
                        }),
                    $('<input type="button"/>')
                        .val("Discard Review")
                        .click(function(e) {
                            gEditCount--;
                            review.deleteReview({
                                buttons: buttons
                            });
                        }),
                    $('<input type="button"/>')
                        .val("Cancel")
                        .click(function() {
                            gEditCount--;
                        }),
                    $('<input type="button"/>')
                        .val("Save")
                        .click(function() {
                            saveReview();
                            return false;
                        })
                ]
            })
            .keypress(function(e) { e.stopPropagation(); })
            .trigger("ready");

        buttons = $("input", dlg);

        var body_classes = ["body-top", "body-bottom"];

        for (var i in body_classes) {
            var cls = body_classes[i];
            $("." + cls, dlg)
                .inlineEditor({
                    cls: cls + "-editor",
                    extraHeight: 50,
                    forceOpen: true,
                    multiline: true,
                    notifyUnchangedCompletion: true,
                    showButtons: false,
                    showEditIcon: false
                })
                .bind("beginEdit", function() {
                    gEditCount++;
                })
                .bind("cancel complete", function() {
                    gEditCount--;
                });
        }

        $("textarea:first", dlg).focus();
        dlg.attr("scrollTop", 0);

        loadDiffFragments("review_draft_diff_comments",
                          "review_draft_comment_container");
    }

    /*
     * Saves the review.
     *
     * This sets the ship_it and body values, and saves all comments.
     */
    function saveReview(publish) {
        $.funcQueue("reviewForm").clear();

        $(".body-top, .body-bottom").inlineEditor("save");

        $(".comment-editable", dlg).each(function() {
            var editable = $(this);
            var comment = editable.data('comment');
            var issue = editable.next()[0];
            var issueOpened = issue ? issue.checked : false;

            if (editable.inlineEditor("dirty") ||
                issueOpened != comment.issue_opened) {
                comment.issue_opened = issueOpened;
                $.funcQueue("reviewForm").add(function() {
                    editable
                        .one("saved", $.funcQueue("reviewForm").next)
                        .inlineEditor("save");
              });
            }
        });

        $.funcQueue("reviewForm").add(function() {
            review.ship_it = $("#id_shipit", dlg)[0].checked;
            review.body_top = $(".body-top", dlg).text();;
            review.body_bottom = $(".body-bottom", dlg).text();;

            var options = {
                buttons: buttons,
                success: $.funcQueue("reviewForm").next
            };

            gEditCount--;

            if (publish) {
                review.publish(options);
            }
            else {
                review.save(options);
            }
        });

        $.funcQueue("reviewForm").add(function() {
            dlg.modalBox("destroy");

            if (publish) {
                hideReviewBanner();
                gReviewBanner.queue(function() {
                    window.location = gReviewRequestPath;
                });
            } else {
                showReviewBanner();
            }
        });

        $.funcQueue("reviewForm").start();
    }
};


/*
 * Adds inline editing capabilities to a comment in the review form.
 *
 * @param {object} comment  A RB.DiffComment, RB.FileAttachmentComment
 *                          or RB.ScreenshotComment instance
 *                          to store the text on and save.
 */
$.fn.reviewFormCommentEditor = function(comment) {
    var self = this;

    return this
        .inlineEditor({
            extraHeight: 50,
            forceOpen: true,
            multiline: true,
            notifyUnchangedCompletion: true,
            showButtons: false,
            showEditIcon: false,
            useEditIconOnly: false
        })
        .bind("beginEdit", function() {
            gEditCount++;
        })
        .bind("cancel", function() {
            gEditCount--;
        })
        .bind("complete", function(e, value) {
            gEditCount--;
            comment.text = value;
            comment.save({
                success: function() {
                    self.trigger("saved");
                }
            });
        })
        .data('comment', comment);
};


/*
 * Adds inline editing capabilities to close description for a review request
 * which have been submitted or discarded.
 *
 * @param {int} type  1: RB.ReviewRequest.CLOSE_DISCARDED
 *                    2: RB.ReviewRequest.CLOSE_SUBMITTED
 */
$.fn.reviewCloseCommentEditor = function(type) {
    return this
        .inlineEditor({
            editIconPath: MEDIA_URL + "rb/images/edit.png?" + MEDIA_SERIAL,
            multiline: true,
            startOpen: false
        })
        .bind("complete", function(e, value) {
            gReviewRequest.close({
                type: type,
                description: value
            });
        });
}


/*
 * Adds inline editing capabilities to a field for a review request.
 */
$.fn.reviewRequestFieldEditor = function() {
    return this.each(function() {
        $(this)
            .inlineEditor({
                cls: this.id + "-editor",
                editIconPath: MEDIA_URL + "rb/images/edit.png?" + MEDIA_SERIAL,
                multiline: this.tagName == "PRE",
                showButtons: !$(this).hasClass("screenshot-editable"),
                startOpen: this.id == "changedescription",
                useEditIconOnly: $(this).hasClass("comma-editable")
            })
            .bind("beginEdit", function() {
                gEditCount++;
            })
            .bind("cancel", function() {
                gEditCount--;
            })
            .bind("complete", function(e, value) {
                gEditCount--;
                setDraftField(this.id, value);
            });
    });
}


/*
 * Handles interaction and events with a screenshot thumbnail.

 * @return {jQuery} The provided screenshot containers.
 */
$.fn.screenshotThumbnail = function() {
    return $(this).each(function() {
        var self = $(this);

        var screenshot_id = self.attr("data-screenshot-id");
        var screenshot = gReviewRequest.createScreenshot(screenshot_id);
        var captionEl = self.find(".screenshot-caption");

        captionEl.find("a.edit")
            .inlineEditor({
                cls: this.id + "-editor",
                editIconPath: MEDIA_URL + "rb/images/edit.png?" + MEDIA_SERIAL,
                showButtons: false
            })
            .bind("beginEdit", function() {
                gEditCount++;
            })
            .bind("cancel", function() {
                gEditCount--;
            })
            .bind("complete", function(e, value) {
                gEditCount--;
                screenshot.ready(function() {
                    screenshot.caption = value;
                    screenshot.save({
                        buttons: gDraftBannerButtons,
                        success: function(rsp) {
                            gDraftBanner.show();
                        }
                    });
                });
            });

        captionEl.find("a.delete")
            .click(function() {
                screenshot.ready(function() {
                    screenshot.deleteScreenshot()
                    self.empty();
                    gDraftBanner.show();
                });

                return false;
            });
    });
}


/*
 * Adds a new, dynamic thumbnail to the thumbnail list.
 *
 * If a screenshot object is given, then this will display actual
 * thumbnail data. Otherwise, this will display a spinner.
 *
 * @param {object} screenshot  The optional screenshot to display.
 *
 * @return {jQuery} The root screenshot thumbnail div.
 */
$.newScreenshotThumbnail = function(screenshot) {
    var container = $('<div/>')
        .addClass("screenshot-container");

    var body = $('<div class="screenshot"/>')
        .addClass("screenshot")
        .appendTo(container);

    var captionArea = $('<div/>')
        .addClass("screenshot-caption")
        .appendTo(container);

    if (screenshot) {
        body.append($("<a/>")
            .attr("href", "s/" + screenshot.id + "/")
            .append($("<img/>")
                .attr({
                    src: screenshot.thumbnail_url,
                    alt: screenshot.caption
                })
            )
        );

        captionArea
            .append($("<a/>")
                .addClass("screenshot-editable edit")
                .attr({
                    href: "#",
                    id: "screenshot_" + screenshot.id + "_caption"
                })
                .text(screenshot.caption)
            )
            .append($("<a/>")
                .addClass("delete")
                .attr("href", "#")
                .append($("<img/>")
                    .attr({
                        src: MEDIA_URL + "rb/images/delete.png?" +
                             MEDIA_SERIAL,
                        alt: "Delete Screenshot"
                    })
                )
            );

        container
            .attr("data-screenshot-id", screenshot.id)
            .screenshotThumbnail();
    } else {
        body.addClass("loading");

        captionArea.append("&nbsp;");
    }

    var thumbnails = $("#screenshot-thumbnails");
    $(thumbnails.parent()[0]).show();
    return container.insertBefore(thumbnails.find("br"));
};


/*
 * Handles interaction and events with a file attachment.

 * @return {jQuery} The provided file attachment container.
 */
$.fn.fileAttachment = function() {
    return $(this).each(function() {
        var self = $(this);

        var fileID = self.attr("data-file-id");
        var fileAttachment = gReviewRequest.createFileAttachment(fileID);
        var draftComment = null;
        var comments = [];
        var commentsProcessed = false;

        self.find("a.edit")
            .inlineEditor({
                cls: "file-" + fileID + "-editor",
                editIconPath: MEDIA_URL + "rb/images/edit.png?" + MEDIA_SERIAL,
                showButtons: false
            })
            .bind("beginEdit", function() {
                gEditCount++;
            })
            .bind("cancel", function() {
                gEditCount--;
            })
            .bind("complete", function(e, value) {
                gEditCount--;
                fileAttachment.ready(function() {
                    fileAttachment.caption = value;
                    fileAttachment.save({
                        buttons: gDraftBannerButtons,
                        success: function(rsp) {
                            gDraftBanner.show();
                        }
                    });
                });
            });

        var addCommentButton =
            self.find('.file-add-comment a')
                .click(function() {
                    showCommentDlg();
                    return false;
                });

        self.find("a.delete")
            .click(function() {
                fileAttachment.ready(function() {
                    fileAttachment.deleteFileAttachment()
                    self.empty();
                    gDraftBanner.show();
                });

                return false;
            });

        function showCommentDlg() {
            gCommentDlg
                .one("close", function() {
                    processComments();
                    createDraftComment();

                    gCommentDlg
                        .setDraftComment(draftComment)
                        .setCommentsList(comments, "file_attachment_comments")
                        .positionToSide(addCommentButton, {
                            side: 'b',
                            fitOnScreen: true
                        });
                    gCommentDlg.open();
                })
                .close();
        }

        function processComments() {
            if (commentsProcessed) {
                return;
            }

            var attachmentComments = gFileAttachmentComments[fileID];

            if (attachmentComments && attachmentComments.length > 0) {
                for (var i in attachmentComments) {
                    var comment = attachmentComments[i];

                    if (comment.localdraft) {
                        createDraftComment(comment.comment_id, comment.text);
                    } else {
                        comments.push(comment);
                    }
                }
            }

            commentsProcessed = true;
        }

        function createDraftComment(commentID, text) {
            if (draftComment != null) {
                return;
            }

            var self = this;
            var review = gReviewRequest.createReview();
            draftComment = review.createFileAttachmentComment(commentID,
                                                              fileID);

            if (text) {
                draftComment.text = text;
            }

            $.event.add(draftComment, "saved", function() {
                showReviewBanner();
            });
        }
    });
}


/*
 * Adds a file to the file attachments list.
 *
 * If an FileAttachment object is given, then this will display the
 * file data. Otherwise, this will display a placeholder.
 *
 * @param {object} fileAttachment  The optional file to display.
 *
 * @return {jQuery} The root file attachment div.
 */
$.newFileAttachment = function(fileAttachment) {
    var container = $('<div/>')
        .addClass('file-container');

    var body = $('<div/>')
        .addClass('file')
        .appendTo(container);

    var actions = $('<ul/>')
        .addClass('actions')
        .appendTo(body);

    var fileHeader = $('<div/>')
        .addClass('file-header')
        .appendTo(body);

    var fileCaption = $('<div/>')
        .addClass('file-caption')
        .append($('<a/>')
            .addClass('edit'))
        .appendTo(body);

    if (fileAttachment) {
        container.attr('data-file-id', fileAttachment.id);

        actions.append($('<li/>')
            .addClass('file-add-comment')
            .append($('<a/>')
                .attr('href', '#')
                .text('Add Comment')));

        fileHeader
            .append($('<img/>')
                .attr('src', fileAttachment.icon_url))
            .append(' ')
            .append($('<a/>')
                .attr('href', fileAttachment.url)
                .text(fileAttachment.filename))
            .append(' ')
            .append($('<a/>')
                .addClass('delete')
                .attr('href', '#')
                .append($('<img/>')
                    .attr({
                        src: MEDIA_URL + 'rb/images/delete.png?' +
                             MEDIA_SERIAL,
                        alt: 'Delete File'
                    })));

        fileCaption.find('a')
            .attr('href', fileAttachment.url)
            .text(fileAttachment.caption);
    }

    container.fileAttachment();

    var attachments = $("#file-list");
    $(attachments.parent()[0]).show();
    return container.insertBefore(attachments.find("br"));
};


/*
 * Sets the list of file attachment comments.
 */
function setFileAttachmentComments(comments) {
    gFileAttachmentComments = comments;
}


/*
 * Registers for updates to the review request. This will cause a pop-up
 * bubble to be displayed when updates of the specified type are displayed.
 *
 * @param {string} lastTimestamp  The last known update timestamp for
 *                                comparison purposes.
 * @param {string} type           The type of update to watch for, or
 *                                undefined for all types.
 */
function registerForUpdates(lastTimestamp, type) {
    function updateFavIcon(url) {
        var head = $("head");
        head.find("link[rel=icon]").remove();
        head.append($("<link/>")
            .attr({
                href: url,
                rel: "icon",
                type: "image/x-icon"
            }));
    }

    var bubble = $("#updates-bubble");
    var summaryEl;
    var userEl;

    var faviconEl = $("head").find("link[rel=icon]");
    var faviconURL = faviconEl.attr("href");
    var faviconNotifyURL = MEDIA_URL + "rb/images/favicon_notify.ico?" +
                           MEDIA_SERIAL;

    $.event.add(gReviewRequest, "updated", function(evt, info) {
        if (bubble.length == 0) {
            updateFavIcon(faviconNotifyURL);

            bubble = $('<div id="updates-bubble"/>');
            summaryEl = $('<span/>')
                .appendTo(bubble);
            bubble.append(" by ");
            userEl = $('<a href="" id="updates-bubble-user"/>')
                .appendTo(bubble);

            bubble
                .append(
                    $('<span id="updates-bubble-buttons"/>')
                        .append($('<a href="#">Update Page</a>')
                            .click(function() {
                                window.location = gReviewRequestPath;
                                return false;
                            }))
                        .append(" | ")
                        .append($('<a href="#">Ignore</a>')
                            .click(function() {
                                bubble.fadeOut();
                                updateFavIcon(faviconURL);
                                return false;
                            }))
                )
                .appendTo(document.body);
        }

        summaryEl.text(info.summary);
        userEl
            .attr('href', info.user.url)
            .text(info.user.fullname);

        bubble
            .hide()
            .css("position", $.browser.msie && $.browser.version == 6
                             ? "absolute" : "fixed")
            .fadeIn();
    });

    gReviewRequest.beginCheckForUpdates(type, lastTimestamp);
}


/*
 * Shows the review banner.
 */
function showReviewBanner() {
    if (gReviewBanner.is(":hidden")) {
        gReviewBanner
            .slideDown()
            .find(".banner")
                .hide()
                .slideDown();
    }
}


/*
 * Hides the review banner.
 */
function hideReviewBanner() {
    gReviewBanner
        .slideUp()
        .find(".banner")
            .slideUp();
}


/*
 * Queues the load of a diff fragment from the server.
 *
 * This will be added to a list, which will fetch the comments in batches
 * based on file IDs.
 *
 * @param {string} queue_name  The name for this load queue.
 * @param {string} comment_id  The ID of the comment.
 * @param {string} key         The key for this request, using the
 *                             filediff and interfilediff.
 */
function queueLoadDiffFragment(queue_name, comment_id, key) {
    if (!gPendingDiffFragments[queue_name]) {
        gPendingDiffFragments[queue_name] = {};
    }

    if (!gPendingDiffFragments[queue_name][key]) {
        gPendingDiffFragments[queue_name][key] = [];
    }

    gPendingDiffFragments[queue_name][key].push(comment_id);
}


/*
 * Begins the loading of all diff fragments on the page belonging to
 * the specified queue and storing in containers with the specified
 * prefix.
 */
function loadDiffFragments(queue_name, container_prefix) {
    if (!gPendingDiffFragments[queue_name]) {
        return;
    }

    for (var key in gPendingDiffFragments[queue_name]) {
        var comments = gPendingDiffFragments[queue_name][key];
        var url = gReviewRequestPath + "fragments/diff-comments/";

        for (var i = 0; i < comments.length; i++) {
            url += comments[i];

            if (i != comments.length - 1) {
                url += ","
            }
        }

        url += "/?queue=" + queue_name +
               "&container_prefix=" + container_prefix +
               "&" + AJAX_SERIAL;

        $.funcQueue("diff_comments").add(function(url) {
            var e = document.createElement("script");
            e.type = "text/javascript";
            e.src = url;
            document.body.appendChild(e);
        }(url));
    }

    // Clear the list.
    gPendingDiffFragments[queue_name] = {};

    $.funcQueue(queue_name).start();
}


/*
 * Initializes drag-and-drop support.
 *
 * This makes it possible to drag screenshots and other files from a file
 * manager and drop them into Review Board. This requires browser support
 * for HTML 5 file drag-and-drop.
 */
function initDnD() {
    var dropIndicator = null;
    var screenshotDropBox;
    var fileDropBox;
    var middleBox;
    var removeDropIndicatorHandle = null;

    $(document.body)
        .bind("dragenter", function(event) {
            handleDragEnter(event);
        });

    function handleDragEnter(event) {
        if (!dropIndicator) {
            var height = $(window).height();

            dropIndicator = $("<div/>")
                .addClass("drop-indicator")
                .appendTo(document.body)
                .width($(window).width())
                .height(height)
                .bind("dragleave", function(event) {
                    /*
                     * This should check whether we've exited the drop
                     * indicator properly. It'll prevent problems when
                     * transitioning between elements within the indicator.
                     *
                     * Note that while this should work cross-browser,
                     * Firefox 4+ appears broken in that it doesn't send us
                     * dropleave events on exiting the window.
                     *
                     * Also note that it doesn't appear that we need to check
                     * the Y coordinate. X should be 0 in most cases when
                     * leaving, except when dragging over the right scrollbar
                     * in Chrome, when it'll be >= the container width.
                     */
                    if (event.pageX <= 0 ||
                        event.pageX >= dropIndicator.width()) {
                        handleDragExit();
                    }

                    return false;
                })
                .mouseenter(function() {
                    /*
                     * If we get a mouse enter, then the user has moved
                     * the mouse over the drop indicator without there
                     * being any drag-and-drop going on. This is likely due
                     * to the broken Firefox 4+ behavior where dragleave
                     * events when leaving windows aren't firing.
                     */
                    handleDragExit();
                    return false;
                });

            screenshotDropBox = $("<div/>")
                .addClass("dropbox")
                .appendTo(dropIndicator)
                .bind('drop', function(event) {
                    return handleDrop(event, "screenshot");
                });
            var screenshotText = $("<h1/>")
                .text("Drop Screenshot")
                .appendTo(screenshotDropBox);

            middleBox = $("<h2/>")
                .text("or")
                .appendTo(dropIndicator);

            fileDropBox = $("<div/>")
                .addClass("dropbox")
                .appendTo(dropIndicator)
                .bind('drop', function(event) {
                    return handleDrop(event, "file");
                });
            var fileText = $("<h1/>")
                .text("Drop File Attachment")
                .appendTo(fileDropBox);

            var dropBoxHeight = (height - middleBox.height()) / 2;
            $([screenshotDropBox[0], fileDropBox[0]])
                .height(dropBoxHeight)
                .bind("dragover", function() {
                    var dt = event.originalEvent.dataTransfer;

                    if (dt) {
                        dt.dropEffect = "copy";
                    }

                    $(this).addClass("hover");
                    return false;
                })
                .bind("dragleave", function(event) {
                    var dt = event.originalEvent.dataTransfer;

                    if (dt) {
                        dt.dropEffect = "none";
                    }

                    $(this).removeClass("hover");
                });

            screenshotText.css("margin-top", -screenshotText.height() / 2);
            fileText.css("margin-top", -fileText.height() / 2);
        }
    }

    function handleDragExit(closeImmediately) {
        if (dropIndicator == null) {
            return;
        }

        if (removeDropIndicatorHandle) {
            window.clearInterval(removeDropIndicatorHandle);
            removeDropIndicatorHandle = null;
        }

        if (closeImmediately) {
            dropIndicator.fadeOut(function() {
                dropIndicator.remove();
                dropIndicator = null;
            });
        } else {
            removeDropIndicatorHandle = window.setInterval(function() {
                handleDragExit(true);
            }, 1000);
        }
    }

    function handleDrop(event, type) {
        /* Do these early in case we hit some error. */
        event.stopPropagation();
        event.preventDefault();

        var dt = event.originalEvent.dataTransfer;

        var files = dt && dt.files;

        if (!files) {
            return;
        }

        if (type == "screenshot") {
            var foundImages = false;

            for (var i = 0; i < files.length; i++) {
                var file = files[i];

                if (file.type == "image/jpeg" ||
                    file.type == "image/pjpeg" ||
                    file.type == "image/png" ||
                    file.type == "image/bmp" ||
                    file.type == "image/gif" ||
                    file.type == "image/svg+xml") {

                    foundImages = true;

                    uploadScreenshot(file);
                }
            }

            if (foundImages) {
                handleDragExit();
            } else {
                if (dropIndicator) {
                    screenshotDropBox.empty();
                    fileDropBox.empty();
                    middleBox.html("None of the dropped files were valid " +
                                   "images");
                }

                setTimeout(function() {
                    handleDragExit(true);
                }, 1500);
            }
        } else if (type == "file") {
            for (var i = 0; i < files.length; i++) {
                uploadFile(files[i]);
            }

            handleDragExit(true);
        }
    }

    function uploadScreenshot(file) {
        /* Create a temporary screenshot thumbnail. */
        var thumb = $.newScreenshotThumbnail()
            .css("opacity", 0)
            .fadeTo(1000, 1);

        var screenshot = gReviewRequest.createScreenshot();
        screenshot.setFile(file);
        screenshot.save({
            buttons: gDraftBannerButtons,
            success: function(rsp, screenshot) {
                thumb.replaceWith($.newScreenshotThumbnail(screenshot));
                gDraftBanner.show();
            },
            error: function(rsp, msg) {
                thumb.remove();
            }
        });
    }

    function uploadFile(file) {
        /* Create a temporary file listing. */
        var thumb = $.newFileAttachment()
            .css("opacity", 0)
            .fadeTo(1000, 1);

        var fileAttachment = gReviewRequest.createFileAttachment();
        fileAttachment.setFile(file);
        fileAttachment.save({
            buttons: gDraftBannerButtons,
            success: function(rsp, fileAttachment) {
                thumb.replaceWith($.newFileAttachment(fileAttachment));
                gDraftBanner.show();
            },
            error: function(rsp, msg) {
                thumb.remove();
            }
        });
    }
}

$(document).ready(function() {
    /* Provide support for expanding submenus in the action list. */
    var menuitem = null;

    function showMenu() {
        if (menuitem) {
            $("ul", menuitem).fadeOut("fast");
            menuitem = null;
        }

        $("ul", this).fadeIn("fast");
    }

    function hideMenu() {
        menuitem = $(this);
        setTimeout(function() {
            if (menuitem) {
                $("ul", menuitem).fadeOut("fast");
            }
        }, 400);
    }

    $(".actions > li:has(ul.menu)")
        .hover(showMenu, hideMenu)
        .toggle(showMenu, hideMenu);

    $("#btn-draft-publish").click(function() {
        /* Save all the fields if we need to. */
        gPublishing = true;
        var fields = $(".editable:inlineEditorDirty");
        gPendingSaveCount = fields.length;

        if (gPendingSaveCount == 0) {
            publishDraft();
        } else {
            fields.inlineEditor("save");
        }

        return false;
    });

    $("#btn-draft-discard").click(function() {
        gReviewRequest.discardDraft({
            options: gDraftBannerButtons
        });
        return false;
    });

    $("#btn-review-request-discard, #discard-review-request-link")
        .click(function() {
            gReviewRequest.close({
                type: RB.ReviewRequest.CLOSE_DISCARDED,
                buttons: gDraftBannerButtons
            });
            return false;
        });

    $("#link-review-request-close-submitted").click(function() {
        /*
         * This is a non-destructive event, so don't confirm unless there's
         * a draft.
         */
        var submit = true;
        if ($("#draft-banner").is(":visible")) {
            submit = confirm("You have an unpublished draft. If you close " +
                             "this review request, the draft will be " +
                             "discarded. Are you sure you want to close " +
                             "the review request?");
        }

        if (submit) {
            gReviewRequest.close({
                type: RB.ReviewRequest.CLOSE_SUBMITTED,
                buttons: gDraftBannerButtons
            });
        }

        return false;
    });

    $("#btn-review-request-reopen").click(function() {
        gReviewRequest.reopen({
            buttons: gDraftBannerButtons
        });

        return false;
    });

    $("#delete-review-request-link").click(function() {
        var dlg = $("<p/>")
            .text("This deletion cannot be undone. All diffs and reviews " +
                  "will be deleted as well.")
            .modalBox({
                title: "Are you sure you want to delete this review request?",
                buttons: [
                    $('<input type="button" value="Cancel"/>'),
                    $('<input type="button" value="Delete"/>')
                        .click(function(e) {
                            gReviewRequest.deletePermanently({
                                buttons: gDraftBannerButtons.add(
                                    $("input", dlg.modalBox("buttons"))),
                                success: function() {
                                    window.location = SITE_ROOT;
                                }
                            });
                        })
                ]
            });

        return false;
    });

    var pendingReview = gReviewRequest.createReview();

    /* Edit Review buttons. */
    $("#review-link, #review-banner-edit").click(function() {
        $.reviewForm(pendingReview);
    });

    $("#shipit-link").click(function() {
        if (confirm("Are you sure you want to post this review?")) {
            pendingReview.ship_it = true;
            pendingReview.body_top = "Ship It!";
            pendingReview.publish({
                buttons: null,
                success: function() {
                    hideReviewBanner();
                    gReviewBanner.queue(function() {
                        window.location = gReviewRequestPath;
                    });
                }
            });
        }
    });

    /* Review banner's Publish button. */
    $("#review-banner-publish").click(function() {
        pendingReview.publish({
            buttons: $("input", gReviewBanner),
            success: function() {
                hideReviewBanner();
                gReviewBanner.queue(function() {
                    window.location = gReviewRequestPath;
                });
            }
        });
    });

    /* Review banner's Delete button. */
    $("#review-banner-discard").click(function() {
        var dlg = $("<p/>")
            .text("If you discard this review, all related comments will " +
                  "be permanently deleted.")
            .modalBox({
                title: "Are you sure you want to discard this review?",
                buttons: [
                    $('<input type="button" value="Cancel"/>'),
                    $('<input type="button" value="Discard"/>')
                        .click(function(e) {
                            pendingReview.deleteReview({
                                buttons: $("input", gReviewBanner),
                                success: function() {
                                    hideReviewBanner();
                                    gReviewBanner.queue(function() {
                                        window.location = gReviewRequestPath;
                                    });
                                }
                            });
                        })
                ]
            });
    });

    $("pre.reviewtext, #description, #testing_done").each(function() {
        $(this).html(linkifyText($(this).text()));
    });

    /* Toggle the state of a review */
    $(".collapse-button").click(function() {
        $(this).closest(".box").toggleClass('collapsed');
    });

    /* Expand all reviews */
    $("#expand-all").click(function() {
        $(".collapsed").removeClass("collapsed");
        return false;
    });

    gCommentDlg = $("#comment-detail")
        .commentDlg()
        .css("z-index", 999);
    gCommentDlg.appendTo("body");

    $("#submitted-banner #changedescription.editable").reviewCloseCommentEditor(RB.ReviewRequest.CLOSE_SUBMITTED);
    $("#discard-banner #changedescription.editable").reviewCloseCommentEditor(RB.ReviewRequest.CLOSE_DISCARDED);

    if (gUserAuthenticated) {
        if (window["gEditable"]) {
            $(".editable").reviewRequestFieldEditor();
            $(".screenshot-container").screenshotThumbnail();
            $(".file-container").fileAttachment();

            var targetGroupsEl = $("#target_groups");
            var targetPeopleEl = $("#target_people");

            if (targetGroupsEl.length > 0) {
                targetGroupsEl
                    .inlineEditor("field")
                    .bind("beginEdit", function() {
                        gEditCount++;
                    })
                    .bind("cancel complete", function() {
                        gEditCount--;
                    })
                    .reviewsAutoComplete({
                        fieldName: "groups",
                        nameKey: "name",
                        descKey: "display_name",
                        extraParams: {
                            displayname: 1
                        }
                    });
            }

            if (targetPeopleEl.length > 0) {
                targetPeopleEl
                    .inlineEditor("field")
                    .bind("beginEdit", function() {
                        gEditCount++;
                    })
                    .bind("cancel complete", function() {
                        gEditCount--;
                    })
                    .reviewsAutoComplete({
                        fieldName: "users",
                        nameKey: "username",
                        descKey: "fullname",
                        extraParams: {
                            fullname: 1
                        }
                    });
            }

            /*
             * Warn the user if they try to navigate away with unsaved comments.
             *
             * @param {event} evt The beforeunload event.
             *
             * @return {string} The dialog message (needed for IE).
             */
            window.onbeforeunload = function(evt) {
                if (gEditCount > 0) {
                    /*
                     * On IE, the text must be set in evt.returnValue.
                     *
                     * On Firefox, it must be returned as a string.
                     *
                     * On Chrome, it must be returned as a string, but you
                     * can't set it on evt.returnValue (it just ignores it).
                     */
                    var msg = "You have unsaved changes that will " +
                              "be lost if you navigate away from " +
                              "this page.";
                    evt = evt || window.event;

                    evt.returnValue = msg;
                    return msg;
                }
            };

            initDnD();
        }
    }

    loadDiffFragments("diff_fragments", "comment_container");
});

// vim: set et:sw=4:
