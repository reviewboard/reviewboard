// State variables
var gHiddenComments = {};
var gDiffHighlightBorder = null;

// XXX This is temporary
window.gHiddenComments = gHiddenComments;


/*
 * Creates a comment block in the diff viewer.
 *
 * @param {jQuery} beginRow      The first table row to attach to.
 * @param {jQuery} endRow        The last table row to attach to.
 * @param {int}    beginLineNum  The line number to attach to.
 * @param {int}    endLineNum    The line number to attach to.
 * @param {array}  comments      The list of comments in this block.
 *
 * @return {object} The comment block.
 */
RB.DiffCommentBlock = function(beginRow, endRow, beginLineNum, endLineNum,
                               comments) {
    var self = this;

    var table = beginRow.parents("table:first");
    var fileid = table[0].id;

    this.filediff = gFileAnchorToId[fileid];
    this.interfilediff = gInterdiffFileAnchorToId[fileid];
    this.beginLineNum = beginLineNum;
    this.endLineNum = endLineNum;
    this.beginRow = beginRow;
    this.endRow = endRow;
    this.comments = [];
    this.draftComment = null;

    this.el = $("<span/>")
        .addClass("commentflag")
        .append($("<span/>").addClass("commentflag-shadow"))
        .click(function() {
            self.showCommentDlg();
            return false;
        });

    $(window).on("resize", function(evt) {
        self.updateSize();
    });

    var innerFlag = $("<span/>")
        .addClass("commentflag-inner")
        .appendTo(this.el);

    this.countEl = $("<span/>")
        .appendTo(innerFlag);

    if ($.browser.msie && $.browser.version == 6) {
        /*
         * Tooltips for some reason cause comment flags to disappear in IE6.
         * So for now, just fake them and never show them.
         */
        this.tooltip = $("<div/>");
    } else {
        this.tooltip = $.tooltip(this.el, {
            side: "rb"
        }).addClass("comments");
    }

    this.anchor = $("<a/>")
        .attr("name", "file" + this.filediff.id + "line" + this.beginLineNum)
        .addClass("comment-anchor")
        .appendTo(this.el);

    /*
     * Find out if there's any draft comments, and filter them out of the
     * stored list of comments.
     */
    if (comments && comments.length > 0) {
        for (var i in comments) {
            var comment = comments[i];

            if (comment.text) {
                // We load in encoded text, so decode it.
                comment.text = $("<div/>").html(comment.text).text();
            }

            if (comment.localdraft) {
                this._createDraftComment(comment.comment_id, comment.text);
            } else {
                this.comments.push(comment);
            }
        }
    } else {
        this._createDraftComment();
    }

    this.updateCount();
    this.updateTooltip();
    this.updateSize();

    /* Now that we've built everything, add this to the DOM. */
    this.beginRow[0].cells[0].appendChild(this.el[0]);
}

$.extend(RB.DiffCommentBlock.prototype, {
    /*
     * Notifies the user of some update. This notification appears by the
     * comment flag.
     *
     * @param {string} text  The notification text.
     */
    notify: function(text) {
        var offset = this.el.offset();

        var bubble = $("<div/>")
            .addClass("bubble")
            .text(text)
            .appendTo(this.el);

        bubble
            .css({
                left: this.el.width(),
                top:  0,
                opacity: 0
            })
            .animate({
                top: "-=10px",
                opacity: 0.8
            }, 350, "swing")
            .delay(1200)
            .animate({
                top: "+=10px",
                opacity: 0
            }, 350, "swing", function() {
                bubble.remove();
            });
    },

    /*
     * Updates the tooltip contents.
     */
    updateTooltip: function() {
        this.tooltip.empty();
        var list = $("<ul/>");

        if (this.draftComment) {
            $("<li/>")
                .text(this.draftComment.get('text').truncate())
                .addClass("draft")
                .appendTo(list);
        }

        for (var i = 0; i < this.comments.length; i++) {
            $("<li/>")
                .text(this.comments[i].text.truncate())
                .appendTo(list);
        }

        list.appendTo(this.tooltip);
    },

    /*
     * Updates the displayed number of comments in the comment block.
     *
     * If there's a draft comment, it will be added to the count. Otherwise,
     * this depends solely on the number of published comments.
     */
    updateCount: function() {
        var count = this.comments.length;

        if (this.draftComment) {
            count++;
        }

        this.count = count;
        this.countEl.html(this.count);
    },

    /*
     * Updates the size of the comment flag.
     */
    updateSize: function() {
        /*
         * On IE and Safari, the marginTop in getExtents will be wrong.
         * Force a value.
         */
        var extents = this.el.getExtents("m", "t") || -4;
        this.el.css("height",
                    this.endRow.offset().top + this.endRow.outerHeight() -
                    this.beginRow.offset().top - extents);
    },

    /*
     * Shows the comment dialog.
     */
    showCommentDlg: function() {
        this._createDraftComment();

        RB.CommentDialogView.create({
            comment: this.draftComment,
            publishedComments: this.comments,
            publishedCommentsType: 'diff_comments',
            position: {
                y: this.endRow.offset().top + this.endRow.height()
            }
        });
    },

    _createDraftComment: function(id, text) {
        if (this.draftComment != null) {
            return;
        }

        var el = this.el;
        var comment = gReviewRequest.createReview().createDiffComment(
            id, this.filediff, this.interfilediff, this.beginLineNum,
            this.endLineNum);

        if (text) {
            comment.set('text', text);
        }

        comment.on('change:text', this.updateTooltip, this);
        comment.on('destroy', function() {
            this.notify("Comment Deleted");

            this.draftComment = null;

            /* Discard the comment block if empty. */
            if (this.comments.length == 0) {
                el.fadeOut(350, function() { el.remove(); })
                this.anchor.remove();
            } else {
                el.removeClass("draft");
                this.updateCount();
                this.updateTooltip();
            }
        }, this);

        comment.on('saved', function() {
            this.updateCount();
            this.updateTooltip();
            this.notify("Comment Saved");
            RB.DraftReviewBannerView.instance.show();
        }, this);

        this.draftComment = comment;
        el.addClass("draft");
    }
});


/*
 * Highlights a chunk of the diff.
 *
 * This will create and move four border elements around the chunk. We use
 * these border elements instead of setting a border since few browsers
 * render borders on <tbody> tags the same, and give us few options for
 * styling.
 */
$.fn.highlightChunk = function() {
    var firstHighlight = false;

    if (!gDiffHighlightBorder) {
        var borderEl = $("<div/>")
            .addClass("diff-highlight-border")
            .css("position", "absolute");

        gDiffHighlightBorder = {
            top: borderEl.clone().appendTo("#diffs"),
            bottom: borderEl.clone().appendTo("#diffs"),
            left: borderEl.clone().appendTo("#diffs"),
            right: borderEl.clone().appendTo("#diffs")
        };

        firstHighlight = true;
    }

    var el = this.parents("tbody:first, thead:first");

    var borderWidth = gDiffHighlightBorder.left.width();
    var borderHeight = gDiffHighlightBorder.top.height();
    var borderOffsetX = borderWidth / 2;
    var borderOffsetY = borderHeight / 2;

    if ($.browser.msie && $.browser.version <= 8) {
        /* On IE, the black rectangle is too far to the top. */
        borderOffsetY = -borderOffsetY;

        if ($.browser.msie && $.browser.version == 8) {
            /* And on IE8, it's also too far to the left. */
            borderOffsetX = -borderOffsetX;
        }
    }

    var updateQueued = false;
    var oldLeft;
    var oldTop;
    var oldWidth;
    var oldHeight;

    /*
     * Updates the position of the border elements.
     */
    function updatePosition(event) {
        if (event && event.target &&
            event.target != window &&
            !event.target.getElementsByTagName) {

            /*
             * This is not a container. It might be a text node.
             * Ignore it.
             */
            return;
        }

        var offset = el.position();

        if (!offset) {
            return;
        }

        var left = Math.round(offset.left);
        var top = Math.round(offset.top);
        var width = el.outerWidth();
        var height = el.outerHeight();

        if (left == oldLeft &&
            top == oldTop &&
            width == oldWidth &&
            height == oldHeight) {

            /* The position and size haven't actually changed. */
            return;
        }

        var outerHeight = height + borderHeight;
        var outerWidth  = width + borderWidth;
        var outerLeft   = left - borderOffsetX;
        var outerTop    = top - borderOffsetY;

        gDiffHighlightBorder.left.css({
            left: outerLeft,
            top: outerTop,
            height: outerHeight
        });

        gDiffHighlightBorder.top.css({
            left: outerLeft,
            top: outerTop,
            width: outerWidth
        });

        gDiffHighlightBorder.right.css({
            left: outerLeft + width,
            top: outerTop,
            height: outerHeight
        });

        gDiffHighlightBorder.bottom.css({
            left: outerLeft,
            top: outerTop + height,
            width: outerWidth
        });

        oldLeft = left;
        oldTop = top;
        oldWidth = width;
        oldHeight = height;

        updateQueued = false;
    }

    /*
     * Updates the position after 50ms so we don't call updatePosition too
     * many times in response to a DOM change.
     */
    function queueUpdatePosition(event) {
        if (!updateQueued) {
            updateQueued = true;
            setTimeout(function() { updatePosition(event); }, 50);
        }
    }

    $(document)
        .on("DOMNodeInserted.highlightChunk DOMNodeRemoved.highlightChunk",
            queueUpdatePosition);
    $(window).on("resize.highlightChunk", updatePosition);

    if (firstHighlight) {
        /*
         * There seems to be a bug where we often won't get this right
         * away on page load. Race condition, perhaps.
         */
        queueUpdatePosition();
    } else {
        updatePosition();
    }

    return this;
};


/*
 * Adds comment flags to a table.
 *
 * lines is an array of dictionaries grouping together comments on the
 * same line. The dictionaries contain the following keys:
 */
RB.addCommentFlags = function(diffReviewableView, table, lines, key) {
    var remaining = {};

    var prevBeginRowIndex = undefined;

    for (var i in lines) {
        var line = lines[i];
        var numLines = line.num_lines;

        var beginLineNum = line.linenum;
        var endLineNum = beginLineNum + numLines - 1;
        var beginRow = diffReviewableView.findLineNumRow(beginLineNum,
                                                         prevBeginRowIndex);

        if (beginRow != null) {
            prevBeginRowIndex = beginRow.rowIndex;

            var endRow = (endLineNum == beginLineNum
                          ? beginRow
                          : diffReviewableView.findLineNumRow(
                              endLineNum,
                              prevBeginRowIndex,
                              prevBeginRowIndex + numLines - 1));


            /*
             * Note that endRow might be null if it exists in a collapsed
             * region, so we can get away with just using beginRow if we
             * need to.
             */
            new RB.DiffCommentBlock($(beginRow), $(endRow || beginRow),
                                    beginLineNum, endLineNum, line.comments);
        } else {
            remaining[beginLineNum] = line;
        }
    }

    gHiddenComments[key] = remaining;
}


/*
 * Toggles the display state of Whitespace chunks and lines.
 *
 * When a diff is loaded, by default, all whitespace only changes are shown.
 * This function hides the changes shown and show the hidden changes,
 * toggling the state.
 */
function toggleWhitespaceChunks()
{
    var tables = $("table.sidebyside");
    var chunks = tables.children("tbody.whitespace-chunk");

    /* Dim the whole chunk */
    chunks.toggleClass("replace");

    /* Dim the anchor to each chunk in the file list */
    chunks.each(function() {
        var target = this.id.split("chunk")[1];
        $("ol.index a[href='#" + target + "']").toggleClass("dimmed");
    });

    /* Remove chunk identifiers */
    chunks.children(":first-child").toggleClass("first");
    chunks.children(":last-child").toggleClass("last");

    /* Toggle individual lines */
    tables.find("tbody tr.whitespace-line").toggleClass("dimmed");

    /* Toggle the display of the button itself */
    $(".review-request ul.controls li.ws").toggle();

    /* Toggle adjacent chunks, and show the whitespace message */
    tables.children("tbody.whitespace-file").toggle()
                                            .siblings("tbody")
                                                .toggle();
}


/*
 * Read cookie to set user preferences for showing Extra Whitespace or not.
 *
 * Returns true by default, false only if a cookie is set.
 */
function showExtraWhitespace()
{
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(";");
        for (var i in cookies) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie == "show_ew=false") {
                return false;
            }
        }
    }

    return true;
}


/*
 * Write cookie to set user preferences for showing Extra Whitespace or not.
 *
 * This a session cookie.
 */
function setExtraWhitespace(value)
{
    document.cookie="show_ew="+value+"; path=/;";
}


/*
 * Toggles the highlighting state of Extra Whitespace.
 *
 * This function turns off or on the highlighting through the ewhl class.
 */
function toggleExtraWhitespace(init)
{

    /* Toggle the cookie value unless this is the first call */
    if ( init == undefined) {
        toggleExtraWhitespace.show_ew = !toggleExtraWhitespace.show_ew;
        setExtraWhitespace(toggleExtraWhitespace.show_ew);
    }
    else {
        /* Record initial value based on cookie setting */
        toggleExtraWhitespace.show_ew = showExtraWhitespace();

        /* Page is initially loaded with highlighting off */
        if (!toggleExtraWhitespace.show_ew) {
            return;
        }
    }

    /* Toggle highlighting */
    $("#diffs").toggleClass("ewhl");

    /* Toggle the display of the button itself */
    $(".review-request ul.controls li.ew").toggle();
}


$(document).ready(function() {
    if (!window.gRevision) {
        /* We're not running in the diff viewer. No need for setup. */
        return;
    }

    $("ul.controls li a.toggleWhitespaceButton").click(function() {
        toggleWhitespaceChunks();
        return false;
    });

    $("ul.controls li a.toggleExtraWhitespaceButton").click(function() {
        toggleExtraWhitespace();
        return false;
    });

    toggleExtraWhitespace('init');

    /*
     * Make sure any inputs on the page (such as the search box) don't
     * bubble down key presses to the document.
     */
    $("input, textarea").keypress(function(evt) {
        evt.stopPropagation();
    });
});

// vim: set et:
