// State variables
var gPublishing = false;
var gPendingSaveCount = 0;
var gPendingDiffFragments = {};
var gReviewBanner = $("#review-banner");
var gDraftBanner = $("#draft-banner");
var gDraftBannerButtons = $("input", gDraftBanner);
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
        return urlizeList(data,
            function(item) { return item.url; },
            function(item) { return item.username; }
        );
    },
    'description': linkifyText,
    'testing_done': linkifyText
};


/*
 * Converts an array of items to a list of hyperlinks.
 *
 * By default, this will use the item as the URL and as the hyperlink text.
 * By overriding urlFunc and textFunc, the URL and text can be customized.
 *
 * @param {array}    list     The list of items.
 * @param {function} urlFunc  A function to return the URL for an item in
 *                            the list.
 * @param {function} textFunc A function to return the text for an item in
 *                            the list.
 *
 * @return A string containing the HTML markup for the list of hyperlinks.
 */
function urlizeList(list, urlFunc, textFunc) {
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
        /\b([a-z]+:\/\/[-A-Za-z0-9+&@#\/%?=~_()|!:,.;]*([-A-Za-z0-9+@#\/%=~_();|]|))/g,
        function(url) {
            /*
             * We might catch an entity at the end of the URL. This is hard
             * to avoid, since we can't rely on advanced RegExp techniques
             * in all browsers. So, we'll now search for it and prevent it
             * from being part of the URL if it exists.
             *
             * See bug 1069.
             */
            var extra = "";
            var parts = url.match(/^(.*)(&[a-z]+;)$/);

            if (parts != null) {
                /* We caught an entity. Set it free. */
                url = parts[1];
                extra = parts[2];
            }

            return '<a href="' + url + '">' + url + '</a>' + extra;
        });


    /* Linkify /r/#/ review request numbers */
    text = text.replace(
        /(^|\s|&lt;)\/(r\/\d+(\/[-A-Za-z0-9+&@#\/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#\/%=~_()|])?)/g,
        '$1<a href="' + SITE_ROOT + '$2">/$2</a>');

    /* Bug numbers */
    if (gBugTrackerURL != "") {
        text = text.replace(/\b(bug|issue) (#[^.\s]+|#?\d+)/gi,
            function(m1, m2, m3) {
                return '<a href="' + gBugTrackerURL.replace("%s", m3) +
                       '">' + m1 + '</a>';
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
                    var s = data[options.nameKey];

                    if (options.descKey) {
                        s += " <span>(" + data[options.descKey] + ")</span>";
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

        $("<li/>")
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
        yourcommentEl.inlineEditor("startEdit");

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
                .bind("complete", function(e, value) {
                    self.html(linkifyText(self.text()));

                    if (context_type == "body_top" ||
                        context_type == "body_bottom") {
                        review_reply[context_type] = value;
                        obj = review_reply;
                    } else if (context_type == "comment") {
                        obj = new RB.DiffCommentReply(review_reply, null,
                                                      context_id);
                        obj.setText(value);
                    } else if (context_type == "screenshot_comment") {
                        obj = new RB.ScreenshotCommentReply(review_reply, null,
                                                            context_id);
                        obj.setText(value);
                    } else {
                        /* Shouldn't be reached. */
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
            bannersEl.append($("<div/>")
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
            );
        }
    }
};


/*
 * Creates the comment detail dialog for lines in a diff. This handles the
 * maintenance of comment blocks and shows existing comments on a block.
 *
 * @return {jQuery} This jQuery.
 */
$.fn.commentDlg = function() {
    var SLIDE_DISTANCE = 10;
    var COMMENTS_BOX_WIDTH = 280;
    var FORM_BOX_WIDTH = 380;
    var self = this;

    /* State */
    var comment = null;
    var textFieldWidthDiff = 0;
    var textFieldHeightDiff = 0;
    var dirty = false;
    var oldDirty = false;

    /* Page elements */
    var draftForm    = $("#draft-form", this);
    var commentsPane = $("#review_comments", this);
    var commentsList = $("#review_comment_list", this);
    var actionField  = $("#comment_action", draftForm);
    var buttons      = $(".buttons", draftForm);
    var statusField  = $(".status", draftForm);
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
            comment.save();
            self.close();
        });

    var textField    = $("#comment_text", draftForm)
        .keydown(function(e) { e.stopPropagation(); })
        .keypress(function(e) {
            e.stopPropagation();

            switch (e.keyCode) {
                case 10:
                case $.ui.keyCode.ENTER:
                    /* Enter */
                    if (e.ctrlKey) {
                        saveButton.click();
                    }
                    break;

                case $.ui.keyCode.ESCAPE:
                    /* Escape */
                    cancelButton.click();
                    break;

                default:
                    return;
            }
        })
        .keyup(function(e) {
            dirty = dirty || comment.text != textField.val();

            saveButton.attr("disabled", textField.val() == "");

            if (dirty && !oldDirty) {
                statusField.html("This comment has unsaved changes.");
                self.handleResize();

                oldDirty = dirty;
            }

            e.stopPropagation();
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
     * Warn the user if they try to navigate away with unsaved comments.
     *
     * @param {event} evt The beforeunload event.
     *
     * @return {string} The dialog message (needed for IE).
     */
    window.onbeforeunload = function(evt) {
        if (dirty && self.is(":visible")) {
            if (!evt) {
                evt = window.event;
            }

            evt.returnValue = "You have unsaved changes that will be " +
                              "lost if you navigate away from this page.";
            return evt.returnValue;
        }
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
            });

        textField.focus();

        oldDirty = false;
        dirty = false;

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
            self.animate({
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
            .height(250);

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
            dirty = false;

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
                            review.deleteReview({
                                buttons: buttons
                            });
                        }),
                    $('<input type="button"/>')
                        .val("Cancel"),
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

            if (editable.inlineEditor("dirty")) {
                $.funcQueue("reviewForm").add(function() {
                    editable
                        .one("saved", $.funcQueue("reviewForm").next)
                        .inlineEditor("save");
              });
            }
        });

        $.funcQueue("reviewForm").add(function() {
            review.ship_it = $("#id_shipit", dlg)[0].checked ? 1 : 0;
            review.body_top = $(".body-top", dlg).text();;
            review.body_bottom = $(".body-bottom", dlg).text();;

            var options = {
                buttons: buttons,
                success: $.funcQueue("reviewForm").next
            };

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
 * @param {object} comment  A RB.DiffComment or RB.ScreenshotComment instance
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
        .bind("complete", function(e, value) {
            comment.text = value;
            comment.save({
                success: function() {
                    self.trigger("saved");
                }
            });
        });
};


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
            .bind("complete", function(e, value) {
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
            .bind("complete", function(e, value) {
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
                    href: screenshot.image_url,
                    id: "screenshot_" + screenshot.id + "_caption"
                })
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
 * Registers for updates to the review request. This will cause a pop-up
 * bubble to be displayed when updates of the specified type are displayed.
 *
 * @param {string} lastTimestamp  The last known update timestamp for
 *                                comparison purposes.
 * @param {string} type           The type of update to watch for, or
 *                                undefined for all types.
 */
function registerForUpdates(lastTimestamp, type) {
    var bubble = $("#updates-bubble");
    var summaryEl;
    var userEl;

    $.event.add(gReviewRequest, "updated", function(evt, info) {
        if (bubble.length == 0) {
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
 * Initializes screenshot drag-and-drop support.
 *
 * This makes it possible to drag screenshots from a file manager
 * and drop them into Review Board. This requires browser support for the
 * HTML 5 file drag-and-drop.
 */
function initScreenshotDnD() {
    var thumbnails = $("#screenshot-thumbnails");
    var dropIndicator = null;
    var thumbnailsContainer = $(thumbnails.parent()[0]);
    var thumbnailsContainerVisible = thumbnailsContainer.is(":visible");

    thumbnails
        .bind("dragenter", function(event) {
            var dt = event.originalEvent.dataTransfer;
            dt.dropEffect = "copy";
            event.preventDefault();
            return false;
        })
        .bind("dragover", function(event) {
            return false;
        })
        .bind("dragexit", function(event) {
            var dt = event.originalEvent.dataTransfer;

            if (dt) {
                dt.dropEffect = "none";
            }

            handleDragExit(event);
            return false;
        })
        .bind("drop", handleDrop);

    var reviewRequestContainer =
        $(".review-request")
            .bind("dragenter", handleDragEnter)
            .bind("dragexit", handleDragExit);

    function handleDragEnter(event) {
        if (!dropIndicator) {
            dropIndicator = $("<h1/>")
                .css("border", "1px black solid")
                .addClass("drop-indicator")
                .html("Drop screenshots here to upload")
                .appendTo(thumbnails);

            thumbnails.addClass("dragover");

            thumbnailsContainer
                .addClass("sliding")
                .slideDown("normal", function() {
                    thumbnailsContainer.removeClass("sliding");
                    thumbnails.scrollIntoView();
                });
        }

        return true;
    }

    function handleDragExit(event) {
        if (event != null) {
            var offset = reviewRequestContainer.offset();
            var width = reviewRequestContainer.width();
            var height = reviewRequestContainer.height();

            if (event.pageX >= offset.left &&
                event.pageX < offset.left + width &&
                event.pageY >= offset.top &&
                event.pageY < offset.top + height) {
                return true;
            }
        }

        thumbnails.removeClass("dragover");

        if (!thumbnailsContainerVisible) {
            thumbnailsContainer
                .addClass("sliding")
                .slideUp("normal", function() {
                    thumbnailsContainer.removeClass("sliding");
                });
        }

        if (dropIndicator != null) {
            dropIndicator.remove();
            dropIndicator = null;
        }

        return true;
    }

    function handleDrop(event) {
        /* Do these early in case we hit some error. */
        event.stopPropagation();
        event.preventDefault();

        var dt = event.originalEvent.dataTransfer;

        var files = dt && dt.files;

        if (!files) {
            return;
        }

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
            thumbnailsContainerVisible = true;
            handleDragExit(null);
        } else {
            if (dropIndicator) {
                dropIndicator.html("None of the dropped files were valid " +
                                   "images");
            }

            setTimeout(function() {
                handleDragExit(null);
            }, 1500);
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

    $("#actions > li:has(ul.menu)")
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
         * a draft. (TODO)
         */
        gReviewRequest.close({
            type: RB.ReviewRequest.CLOSE_SUBMITTED,
            buttons: gDraftBannerButtons
        });

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

    if (gUserAuthenticated) {
        if (window["gEditable"]) {
            $(".editable").reviewRequestFieldEditor();
            $(".screenshot-container").screenshotThumbnail();

            var targetGroupsEl = $("#target_groups");
            var targetPeopleEl = $("#target_people");

            if (targetGroupsEl.length > 0) {
                targetGroupsEl
                    .inlineEditor("field")
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
                    .reviewsAutoComplete({
                        fieldName: "users",
                        nameKey: "username",
                        descKey: "fullname",
                        extraParams: {
                            fullname: 1
                        }
                    });
            }

            initScreenshotDnD();
        }
    }

    loadDiffFragments("diff_fragments", "comment_container");
});

// vim: set et:sw=4:
