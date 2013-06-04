// State variables
var gReviewBanner = $("#review-banner");


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
    RB.apiCall({
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
        reviewRequestEditor.incr('editCount');

        /* XXX Remove this global when we can. */
        window.gReviewFormDiffQueue = new RB.DiffFragmentQueueView({
            containerPrefix: 'review_draft_comment_container',
            reviewRequestPath: gReviewRequestPath,
            queueName: 'review_draft_diff_comments'
        });

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
                            reviewRequestEditor.decr('editCount');
                            review.destroy({
                                buttons: buttons,
                                success: function() {
                                    RB.DraftReviewBannerView.instance.hideAndReload();
                                }
                            });
                        }),
                    $('<input type="button"/>')
                        .val("Cancel")
                        .click(function() {
                            reviewRequestEditor.decr('editCount');
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
                .on({
                    "beginEdit": function() {
                        reviewRequestEditor.incr('editCount');
                    },
                    "cancel complete": function() {
                        reviewRequestEditor.decr('editCount');
                    }
                });
        }

        $("textarea:first", dlg).focus();
        dlg.attr("scrollTop", 0);

        gReviewFormDiffQueue.loadFragments();
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
            review.set({
                shipIt: $("#id_shipit", dlg)[0].checked,
                bodyTop: $(".body-top", dlg).text(),
                bodyBottom: $(".body-bottom", dlg).text(),
                public: publish
            });

            reviewRequestEditor.decr('editCount');

            review.save({
                buttons: buttons,
                success: $.funcQueue("reviewForm").next,
                error: function() {
                    console.log(arguments);
                }
            });
        });

        $.funcQueue("reviewForm").add(function() {
            var reviewBanner = RB.DraftReviewBannerView.instance;

            dlg.modalBox("destroy");

            if (publish) {
                reviewBanner.hideAndReload();
            } else {
                reviewBanner.show();
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
        .on({
            "beginEdit": function() {
                reviewRequestEditor.incr('editCount');
            },
            "cancel": function() {
                reviewRequestEditor.decr('editCount');
            },
            "complete": function(e, value) {
                reviewRequestEditor.decr('editCount');
                comment.set('text', value);
                comment.save({
                    success: function() {
                        self.trigger("saved");
                    }
                });
            }
        })
        .data('comment', comment);
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
RB.registerForUpdates = function(lastTimestamp, type) {
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
    var faviconNotifyURL = STATIC_URLS["rb/images/favicon_notify.ico"];

    gReviewRequest.on('updated', function(info) {
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
            .text(info.user.fullname || info.user.username);

        bubble
            .hide()
            .css("position", $.browser.msie && $.browser.version == 6
                             ? "absolute" : "fixed")
            .fadeIn();
    });

    gReviewRequest.beginCheckForUpdates(type, lastTimestamp);
}


/*
 * Initializes review request pages.
 *
 * XXX This is a temporary function that exists while we're transitioning
 *     to Backbone.js.
 */
RB.initReviewRequestPage = function() {
    var pendingReview = gReviewRequest.createReview(),
        reviewBanner;

    reviewBanner = RB.DraftReviewBannerView.create({
        el: $('#review-banner'),
        model: pendingReview
    });

    pendingReview.on('destroyed published', function() {
        reviewBanner.hideAndReload();
    });

    /* Edit Review buttons. */
    $("#review-link").click(function() {
        $.reviewForm(pendingReview);
    });

    $("#shipit-link").click(function() {
        if (confirm("Are you sure you want to post this review?")) {
            pendingReview.set({
                shipIt: true,
                bodyTop: 'Ship It!',
                public: true
            });
            pendingReview.save({
                buttons: null,
                success: function() {
                    RB.DraftReviewBannerView.instance.hideAndReload();
                }
            });
        }
    });
}

// vim: set et:sw=4:
