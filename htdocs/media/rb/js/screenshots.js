/*
 * Creates a comment block to the screenshot comments area.
 *
 * @param {int}    x          The X area of the block.
 * @param {int}    y          The Y area of the block.
 * @param {int}    width      The block's width.
 * @param {int}    height     The block's height.
 * @param {jQuery} container  The container for the comment block.
 * @param {array}  comments   The list of comments in this block.
 *
 * @return {object} The comment block.
 */
function CommentBlock(x, y, width, height, container, comments) {
    var self = this;

    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
    this.hasDraft = false;
    this.comments = [];
    this.text = "";
    this.canDelete = false;
    this.type = "screenshot_comment";

    this.el = $('<div class="selection"></div>').appendTo(container);
    this.tooltip = $.tooltip(this.el, {
        side: "lrbt"
    }).addClass("comments");
    this.flag = $('<div class="selection-flag"></div>').appendTo(this.el);

    /*
     * Find out if there's any draft comments, and filter them out of the
     * stored list of comments.
     */
    if (comments && comments.length > 0) {
        for (comment in comments) {
            if (comments[comment].localdraft) {
                this.setText(comments[comment].text);
                this.setHasDraft(true);
                this.canDelete = true;
            } else {
                this.comments.push(comments[comment]);
            }
        }
    } else {
        this.setHasDraft(true);
    }

    this.el
        .move(this.x, this.y, "absolute")
        .width(this.width)
        .height(this.height);

    this.updateCount();
    this.updateTooltip();

    return this;
}

jQuery.extend(CommentBlock.prototype, {
    /*
     * Discards the comment block if it's empty.
     */
    discardIfEmpty: function() {
        if (this.text == "" && this.comments.length == 0) {
            var self = this;
            this.el.fadeOut(350, function() { self.el.remove(); });
        }
    },

    /*
     * Saves the draft text in the comment block to the server.
     */
    save: function() {
        var self = this;

        rbApiCall({
            url: this.getURL(),
            data: {
                action: "set",
                text: this.text
            },
            success: function(data) {
                self.canDelete = true;
                self.setHasDraft(true);
                self.updateCount();

                self.notify("Comment Saved");
                $.reviewBanner();
            }
        });
    },

    /*
     * Deletes the draft comment on the server, discarding the comment block
     * afterward if empty.
     */
    deleteComment: function() {
        if (!this.canDelete) {
            // TODO: Script error. Report it.
            return;
        }

        var self = this;

        rbApiCall({
            url: this.getURL(),
            data: {
                action: "delete"
            },
            success: function() {
                self.canDelete = false;
                self.text = "";
                self.setHasDraft(false);
                self.updateCount();
                self.notify("Comment Deleted", function() {
                    self.discardIfEmpty();
                });
            }
        });
    },

    /*
     * Sets the current text in the comment block.
     *
     * @param {string} text  The new text to set.
     */
    setText: function(text) {
        this.text = text;

        this.updateTooltip();
    },

    /*
     * Updates the tooltip contents.
     */
    updateTooltip: function() {
        function addEntry(text) {
            var item = $("<li>").appendTo(list);
            item.text(text.truncate());
            return item;
        }

        this.tooltip.empty();
        var list = $("<ul/>").appendTo(this.tooltip);

        if (this.text != "") {
            addEntry(this.text).addClass("draft");
        }

        $(this.comments).each(function(i) {
            addEntry(this.text);
        });
    },

    /*
     * Updates the displayed number of comments in the comment block.
     *
     * If there's a draft comment, it will be added to the count. Otherwise,
     * this depends solely on the number of published comments.
     */
    updateCount: function() {
        var count = this.comments.length;

        if (this.hasDraft) {
            count++;
        }

        this.count = count;
        this.flag.html(count);
    },

    /*
     * Sets whether or not this comment block has a draft comment.
     *
     * @param {bool} hasDraft  true if this has a draft comment, or false
     *                         otherwise.
     */
    setHasDraft: function(hasDraft) {
        if (hasDraft) {
            this.el.addClass("draft");
            this.flag.addClass("flag-draft");
        } else {
            this.el.removeClass("draft");
            this.flag.removeClass("flag-draft");
        }

        this.hasDraft = hasDraft;
    },

    /*
     * Notifies the user of some update. This notification appears in the
     * comment area.
     *
     * @param {string} text  The notification text.
     */
    notify: function(text, cb) {
        var offset = this.el.offset();

        var bubble = $("<div></div>")
            .addClass("bubble")
            .appendTo(this.el)
            .text(text);

        bubble
            .css("opacity", 0)
            .move(Math.round((this.el.width()  - bubble.width())  / 2),
                  Math.round((this.el.height() - bubble.height()) / 2))
            .animate({
                top: "-=10px",
                opacity: 0.8
            }, 350, "swing")
            .delay(2000)
            .animate({
                top: "+=10px",
                opacity: 0
            }, 350, "swing", function() {
                bubble.remove();

                if ($.isFunction(cb)) {
                    cb();
                }
            });
    },

    /*
     * Returns the URL used for API calls.
     *
     * @return {string} The URL used for API calls for this comment block.
     */
    getURL: function() {
        return getReviewRequestAPIPath(true) +
               getScreenshotAPIPath(gScreenshotId, this.x, this.y,
                                    this.width, this.height);
    }
});


/*
 * Creates a box for creating and seeing all comments on a screenshot.
 *
 * @param {object} regions  The regions containing comments.
 *
 * @return {jQuery} This jQuery.
 */
jQuery.fn.screenshotCommentBox = function(regions) {
    var self = this;

    /* State */
    var activeCommentBlock = null;

    /* Page elements */
    var image = $("img", this);

    var selectionArea =
        $('<div id="selection-container"></div>')
        .prependTo(this);

    var activeSelection =
        $('<div id="selection-interactive"></div>')
        .prependTo(selectionArea)
        .hide();

    var commentDetail = $("#comment-detail")
        .commentDlg()
        .bind("close", function() { activeCommentBlock = null; })
        .css("z-index", 999)
        .appendTo($("body"));

    /*
     * Register events on the selection area for handling new comment
     * creation.
     */
    $([image[0], selectionArea[0]])
        .mousedown(function(evt) {
            evt.stopPropagation();
            evt.preventDefault();

            if (!activeCommentBlock && evt.which == 1) {
                var offset = selectionArea.offset();
                activeSelection.beginX = evt.pageX - offset.left;
                activeSelection.beginY = evt.pageY - offset.top;

                activeSelection
                    .move(activeSelection.beginX, activeSelection.beginY)
                    .width(1)
                    .height(1)
                    .show();

                if (activeSelection.is(":hidden")) {
                    commentDetail.hide();
                }
            }
        })
        .mouseup(function(evt) {
            if (!activeCommentBlock && activeSelection.is(":visible")) {
                evt.stopPropagation();

                var width  = activeSelection.width();
                var height = activeSelection.height();
                var offset = activeSelection.position();

                activeSelection.hide();

                /*
                 * If we don't pass an arbitrary minimum size threshold,
                 * don't do anything.  This helps avoid making people mad
                 * if they accidentally click on the image.
                 */
                if (width > 5 && height > 5) {
                    if (!activeCommentBlock) {
                        showCommentDlg(addCommentBlock(offset.left,
                                                       offset.top,
                                                       width, height));
                    } else {
                        // TODO: Reposition the old block. */
                    }
                }
            }
        })
        .mousemove(function(evt) {
            if (!activeCommentBlock && activeSelection.is(":visible")) {
                evt.stopPropagation();
                evt.preventDefault();
                var offset = selectionArea.offset();
                var x = evt.pageX - offset.left;
                var y = evt.pageY - offset.top;

                activeSelection
                    .css(activeSelection.beginX <= x
                         ? {
                               left:  activeSelection.beginX,
                               width: x - activeSelection.beginX
                           }
                         : {
                               left:  x,
                               width: activeSelection.beginX - x
                           })
                    .css(activeSelection.beginY <= y
                         ? {
                               top:    activeSelection.beginY,
                               height: y - activeSelection.beginY
                           }
                         : {
                               top:    y,
                               height: activeSelection.beginY - y
                           });
            }
        })

    /*
     * Register a hover event to hide the comments when the mouse is not
     * over the comment area.
     */
    this.hover(
        function() {
            selectionArea.show();
        },
        function() {
            if (activeSelection.is(":hidden") &&
                commentDetail.is(":hidden")) {
                selectionArea.hide();
            }
        }
    );

    /*
     * Register a resize event to reposition the selection area on page
     * resize, so that comments are in the right locations.
     */
    $(window)
        .resize(function() {
            var offset = image.position();

            if ($.browser.msie && $.browser.version == 6) {
                offset.left -= self.getExtents("bmp", "l");
            }

            selectionArea
                .width(image.width())
                .height(image.height())
                .css("left", offset.left);
        })
        .triggerHandler("resize");

    /* Add all existing comment regions to the page. */
    for (region in regions) {
        var comments = regions[region];
        addCommentBlock(comments[0].x, comments[0].y,
                        comments[0].w, comments[0].h,
                        comments);
    }

    /*
     * Adds a new comment block to the selection area. This may contain
     * existing comments or may be a newly created comment block.
     *
     * @param {int}   x         The X area of the block.
     * @param {int}   y         The Y area of the block.
     * @param {int}   width     The block's width.
     * @param {int}   height    The block's height.
     * @param {array} comments  The list of comments in this block.
     *
     * @return {CommentBlock} The new comment block.
     */
    function addCommentBlock(x, y, width, height, comments) {
        var commentBlock = new CommentBlock(x, y, width, height,
                                            selectionArea, comments)
        commentBlock.el.click(function() {
            showCommentDlg(commentBlock);
        });

        return commentBlock;
    }

    /*
     * Shows the comment details dialog for a comment block.
     *
     * @param {CommentBlock} commentBlock  The comment block to show.
     */
    function showCommentDlg(commentBlock) {
        commentDetail
            .one("close", function() {
                activeCommentBlock = commentBlock;
                commentDetail
                    .setCommentBlock(commentBlock)
                    .positionToSide(commentBlock.flag, {
                        side: 'b',
                        fitOnScreen: true
                    });
                commentDetail.open();
            })
            .close()
    }

    return this;
}

// vim: set et ts=4:
