// State variables
var gReviewBanner = $("#review-banner");


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
        RB.ReviewDialogView.create({
            review: pendingReview
        });
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
