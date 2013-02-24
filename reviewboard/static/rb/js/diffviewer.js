// Constants
var BACKWARD = -1;
var FORWARD  = 1;
var INVALID  = -1;
var DIFF_SCROLLDOWN_AMOUNT = 100;
var VISIBLE_CONTEXT_SIZE = 5;

var ANCHOR_COMMENT = 1;
var ANCHOR_FILE = 2;
var ANCHOR_CHUNK = 4;


// State
var gDiff,
    gCollapseButtons = [];


/*
 * A list of key bindings for the page.
 */
var gActions = [
    { // Previous file
        keys: "aAKP<m",
        onPress: function() {
            scrollToAnchor(GetNextAnchor(BACKWARD, ANCHOR_FILE));
        }
    },

    { // Next file
        keys: "fFJN>",
        onPress: function() {
            scrollToAnchor(GetNextAnchor(FORWARD, ANCHOR_FILE));
        }
    },

    { // Previous diff
        keys: "sSkp,,",
        onPress: function() {
            scrollToAnchor(GetNextAnchor(BACKWARD, ANCHOR_CHUNK | ANCHOR_FILE));
        }
    },

    { // Next diff
        keys: "dDjn..",
        onPress: function() {
            scrollToAnchor(GetNextAnchor(FORWARD, ANCHOR_CHUNK | ANCHOR_FILE));
        }
    },

    { // Recenter
        keys: unescape("%0D"),
        onPress: function() { scrollToAnchor($(gAnchors[gSelectedAnchor])); }
    },

    { // Previous comment
        keys: "[x",
        onPress: function() {
            scrollToAnchor(GetNextAnchor(BACKWARD, ANCHOR_COMMENT));
        }
    },

    { // Next comment
        keys: "]c",
        onPress: function() {
            scrollToAnchor(GetNextAnchor(FORWARD, ANCHOR_COMMENT));
        }
    },

    { // Go to header
        keys: "gu;",
        onPress: function() {}
    },

    { // Go to footer
        keys: "GU:",
        onPress: function() {}
    }
];


// State variables
var gSelectedAnchor = INVALID;
var gFileAnchorToId = {};
var gInterdiffFileAnchorToId = {};
var gAnchors = $();
var gHiddenComments = {};
var gDiffHighlightBorder = null;
var gStartAtAnchor = null;


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
function DiffCommentBlock(beginRow, endRow, beginLineNum, endLineNum,
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

$.extend(DiffCommentBlock.prototype, {
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
                .text(this.draftComment.text.truncate())
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

        var self = this;
        var el = this.el;
        var comment = gReviewRequest.createReview().createDiffComment(
            id, this.filediff, this.interfilediff, this.beginLineNum,
            this.endLineNum);

        if (text) {
            comment.text = text;
        }

        $.event.add(comment, "textChanged", function() {
            self.updateTooltip();
        });

        $.event.add(comment, "deleted", function() {
            self.notify("Comment Deleted");
        });

        $.event.add(comment, "destroyed", function() {
            self.draftComment = null;

            /* Discard the comment block if empty. */
            if (self.comments.length == 0) {
                el.fadeOut(350, function() { el.remove(); })
                self.anchor.remove();
            } else {
                el.removeClass("draft");
                self.updateCount();
                self.updateTooltip();
            }
        });

        $.event.add(comment, "saved", function() {
            self.updateCount();
            self.updateTooltip();
            self.notify("Comment Saved");
            showReviewBanner();
        });

        this.draftComment = comment;
        el.addClass("draft");
    }
});


/*
 * Registers a section as being a diff file.
 *
 * This handles all mouse actions on the diff, comment range selection, and
 * populatation of comment flags.
 *
 * @param {array}  lines  The lines containing comments. See the
 *                        addCommentFlags documentation for the format.
 * @param {string} key    A unique ID identifying the file the comments
 *                        belong too (typically based on the filediff_id).
 *
 * @return {jQuery} The diff file element.
 */
$.fn.diffFile = function(lines, key) {
    return this.each(function() {
        var self = $(this);

        /* State */
        var selection = {
            begin: null,
            beginNum: 0,
            end: null,
            endNum: 0,
            lastSeenIndex: 0
        };

        var ghostCommentFlag = $("<span/>")
            .addClass("commentflag")
            .addClass("ghost-commentflag")
            .append($("<span class='commentflag-shadow'/>"))
            .append($("<span class='commentflag-inner'/>"))
            .mousedown(function(e) { self.triggerHandler("mousedown", e); })
            .mouseup(function(e)   { self.triggerHandler("mouseup", e);   })
            .mouseover(function(e) { self.triggerHandler("mouseover", e); })
            .mouseout(function(e)  { self.triggerHandler("mouseout", e);  })
            .hide()
            .appendTo("body");

        var ghostCommentFlagCell = null;


        /* Events */
        self
            .mousedown(function(e) {
                /*
                 * Handles the mouse down event, which begins selection for
                 * comments.
                 *
                 * @param {event} e  The mousedown event.
                 */
                var node = e.target;

                if (ghostCommentFlagCell != null) {
                    node = ghostCommentFlagCell[0];
                }

                if (isLineNumCell(node)) {
                    beginSelection($(node.parentNode));
                    return false;
                }

                return true;
            })
            .mouseup(function(e) {
                /*
                 * Handles the mouse up event, which finalizes selection
                 * of a range of lines.
                 *
                 * This will create a new comment block and display the
                 * comment dialog.
                 *
                 * @param {event} e  The mouseup event.
                 */
                var node = e.target;

                if (ghostCommentFlagCell != null) {
                    node = ghostCommentFlagCell[0];
                }

                if (isLineNumCell(node)) {
                    endSelection(getActualLineNumCell($(node)).parent());
                } else {
                    /*
                     * The user clicked somewhere else. Move the anchor
                     * point here if it's part of the diff.
                     */
                    var tbody = $(node).parents("tbody:first");

                    if (tbody.length > 0 &&
                        (tbody.hasClass("delete") || tbody.hasClass("insert") ||
                         tbody.hasClass("replace"))) {
                        gotoAnchor($("a:first", tbody).attr("name"), true);
                    }
                }

                resetSelection();

                return false;
            })
            .mouseover(function(e) {
                /*
                 * Handles the mouse over event. This will update the
                 * selection, if there is one, to include this row in the
                 * range, and set the "selected" class on the new row.
                 *
                 * @param {event} e  The mouseover event.
                 */
                var node = getActualLineNumCell($(e.target));
                var row = node.parent();

                if (isLineNumCell(node[0])) {
                    addRowToSelection(row);
                } else if (ghostCommentFlagCell != null &&
                           node[0] != ghostCommentFlagCell[0]) {
                    row.removeClass("selected");
                }
            })
            .mouseout(function(e) {
                /*
                 * Handles the mouse out event, removing any lines outside
                 * the new range from the selection.
                 *
                 * @param {event} e  The mouseout event.
                 */
                var relTarget = e.relatedTarget,
                    node = getActualLineNumCell($(e.target));

                if (relTarget != ghostCommentFlag[0]) {
                    ghostCommentFlag.hide();
                    ghostCommentFlagCell = null;
                }

                if (selection.begin != null) {
                    if (relTarget != null && isLineNumCell(relTarget)) {
                        removeOldRowsFromSelection($(relTarget.parentNode));
                    }
                } else if (node != null && isLineNumCell(node[0])) {
                    /*
                     * Opera seems to generate lots of spurious mouse-out
                     * events, which would cause us to get all sorts of
                     * errors in here unless we check the target above.
                     */
                    node.parent().removeClass("selected");
                }
            })
            .on({
                "touchmove": function(e) {
                    var firstTouch = e.originalEvent.targetTouches[0];
                    var target = document.elementFromPoint(firstTouch.pageX,
                                                        firstTouch.pageY);
                    var node = getActualLineNumCell($(target));
                    var row = node.parent();

                    if (selection.lastSeenIndex == row[0].rowIndex) {
                        return;
                    }

                    if (isLineNumCell(node[0])) {
                        var row = node.parent();
                        removeOldRowsFromSelection(row);
                        addRowToSelection(row);
                    }
                },
                "touchcancel": function(e) {
                    resetSelection();
                }
            })
            .proxyTouchEvents("touchstart touchend");

        addCommentFlags(self, lines, key);

        /*
         * Begins the selection of line numbers.
         *
         * @param {jQuery} row  The row to begin the selection on.
         */
        function beginSelection(row) {
            selection.begin    = selection.end    = row;
            selection.beginNum = selection.endNum =
                parseInt(row.attr('line'), 10);

            selection.lastSeenIndex = row[0].rowIndex;
            row.addClass("selected");

            self.disableSelection();
        }

        /*
         * Finalizes the selection and pops up a comment dialog.
         *
         * @param {jquery} row  The row to end the selection on.
         */
        function endSelection(row) {
            row.removeClass("selected");

            if (selection.beginNum == selection.endNum) {
                /* See if we have a comment flag on the selected row. */
                var commentFlag = row.find(".commentflag");

                if (commentFlag.length == 1) {
                    commentFlag.click()
                    return;
                }
            }

            /*
             * Selection was finalized. Create the comment block
             * and show the comment dialog.
             */
            var commentBlock = new DiffCommentBlock(
                selection.begin,
                selection.end,
                selection.beginNum,
                selection.endNum);
            commentBlock.showCommentDlg();
        }

        /*
         * Adds a row to the selection. This will update the selection range
         * and mark the rows as selected.
         *
         * This row is assumed to be the most recently selected row, and
         * will mark the new beginning or end of the selection.
         *
         * @param {jQuery} row  The row to add to the selection.
         */
        function addRowToSelection(row) {
            if (selection.begin != null) {
                /* We have an active selection. */
                var linenum = parseInt(row.attr("line"), 10);

                if (linenum < selection.beginNum) {
                    selection.beginNum = linenum;
                    selection.begin = row;
                } else if (linenum > selection.beginNum) {
                    selection.end = row;
                    selection.endNum = linenum;
                }

                var min = Math.min(selection.lastSeenIndex,
                                   row[0].rowIndex);
                var max = Math.max(selection.lastSeenIndex,
                                   row[0].rowIndex);

                for (var i = min; i <= max; i++) {
                    $(self[0].rows[i]).addClass("selected");
                }

                selection.lastSeenIndex = row[0].rowIndex;
            } else {
                var lineNumCell = row[0].cells[0];

                /* See if we have a comment flag in here. */
                if ($(".commentflag", lineNumCell).length == 0) {
                    ghostCommentFlag
                        .css("top", row.offset().top - 1)
                        .show()
                        .parent()
                            .removeClass("selected");
                    ghostCommentFlagCell = $(row[0].cells[0]);
                }

                row.addClass("selected");
            }
        }

        /*
         * Removes any old rows from the selection, based on the most recent
         * row selected.
         *
         * @param {jQuery} row  The last row selected.
         */
        function removeOldRowsFromSelection(row) {
            var destRowIndex = row[0].rowIndex;

            if (destRowIndex >= selection.begin[0].rowIndex) {
                for (var i = selection.lastSeenIndex;
                     i > destRowIndex;
                     i--) {
                    $(self[0].rows[i]).removeClass("selected");
                }

                selection.lastSeenIndex = destRowIndex;
            }
        }

        /*
         * Resets the selection information.
         */
        function resetSelection() {
            if (selection.begin != null) {
                /* Reset the selection. */
                var rows = self[0].rows;

                for (var i = selection.begin[0].rowIndex;
                     i <= selection.end[0].rowIndex;
                     i++) {
                    $(rows[i]).removeClass("selected");
                }

                selection.begin    = selection.end    = null;
                selection.beginNum = selection.endNum = 0;
                selection.rows = [];
            }

            ghostCommentFlagCell = null;

            /* Re-enable text selection on IE */
            self.enableSelection();
        }

        /*
         * Returns whether a particular cell is a line number cell.
         *
         * @param {HTMLElement} cell  The cell element.
         *
         * @return {bool} true if the cell is the line number cell.
         */
        function isLineNumCell(cell) {
            return (cell.tagName == "TH" &&
                    cell.parentNode.getAttribute('line'));
        }


        /*
         * Returns the actual cell node in the table.
         *
         * If the node specified is the ghost flag, this will return the
         * cell the ghost flag represents.
         *
         * If this is a comment flag inside a cell, this will return the
         * comment flag's parent cell
         *
         * @return {jQuery} The row.
         */
        function getActualLineNumCell(node) {
            if (node.hasClass("commentflag")) {
                if (node[0] == ghostCommentFlag[0]) {
                    node = ghostCommentFlagCell;
                } else {
                    node = node.parent();
                }
            }

            return node;
        }
    });
};


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
 * Sets the active anchor on the page, optionally scrolling to it.
 *
 * @param {string} name    The anchor name.
 * @param {bool}   scroll  If true, scrolls the page to the anchor.
 */
function gotoAnchor(name, scroll) {
    return scrollToAnchor($("a[name='" + name + "']"), scroll || false);
}


/*
 * Finds the row in a table matching the specified line number.
 *
 * @param {HTMLElement} table     The table element.
 * @param {int}         linenum   The line number to search for.
 * @param {int}         startRow  Optional start row to search.
 * @param {int}         endRow    Optional end row to search.
 *
 * @param {HTMLElement} The resulting row, or null if not found.
 */
function findLineNumRow(table, linenum, startRow, endRow) {
    var row = null;
    var row_offset = 1; // Get past the headers.

    if (table.rows.length - row_offset > linenum) {
        row = table.rows[row_offset + linenum];

        // Account for the "x lines hidden" row.
        if (row != null && parseInt(row.getAttribute('line'), 10) == linenum) {
            return row;
        }
    }

    if (startRow) {
        // startRow already includes the offset, so we need to remove it
        startRow -= row_offset;
    }

    var low = startRow || 1;
    var high = Math.min(endRow || table.rows.length, table.rows.length);

    if (endRow != undefined && endRow < table.rows.length) {
        /* See if we got lucky and found it in the last row. */
        if (parseInt(table.rows[endRow].getAttribute('line'), 10) == linenum) {
            return table.rows[endRow];
        }
    } else if (row != null) {
        /*
         * We collapsed the rows (unless someone mucked with the DB),
         * so the desired row is less than the row number retrieved.
         */
        high = Math.min(high, row_offset + linenum);
    }

    /* Binary search for this cell. */
    for (var i = Math.round((low + high) / 2); low < high - 1;) {
        row = table.rows[row_offset + i];

        if (!row) {
            /*
             * should not happen, unless we miscomputed high
             */
            high--;
            /*
             * will not do much if low + high is odd
             * but we'll catch up on the next iteration
             */
            i = Math.round((low + high) / 2);
            continue;
        }

        var value = parseInt(row.getAttribute('line'), 10);

        if (!value) {
            /*
             * bad luck, let's look around.
             * We'd expect to find a value on the first try
             * but the following makes sure we explore all
             * rows
             */
            var found = false;

            for (var k = 1; k <= (high-low) / 2; k++) {
                row = table.rows[row_offset + i + k];
                if (row && parseInt(row.getAttribute('line'), 10)) {
                    i = i + k;
                    found = true;
                    break;
                } else {
                    row = table.rows[row_offset + i - k];
                    if (row && parseInt(row.getAttribute('line'), 10)) {
                        i = i - k;
                        found = true;
                        break;
                    }
                }
            }

            if (found) {
                value = parseInt(row.getAttribute('line'), 10);
            } else {
                return null;
            }
        }

        /* See if we can use simple math to find the row quickly. */
        var guessRowNum = linenum - value + row_offset + i;

        if (guessRowNum >= 0 && guessRowNum < table.rows.length) {
            var guessRow = table.rows[guessRowNum];

            if (guessRow
                && parseInt(guessRow.getAttribute('line'), 10) == linenum) {
                /* We found it using maths! */
                return guessRow;
            }
        }

        var oldHigh = high;
        var oldLow = low;

        if (value > linenum) {
            high = i;
        } else if (value < linenum) {
            low = i;
        } else {
            return row;
        }

        /*
         * Make sure we don't get stuck in an infinite loop. This can happen
         * when a comment is placed in a line that isn't being shown.
         */
        if (oldHigh == high && oldLow == low) {
            break;
        }

        i = Math.round((low + high) / 2);
    }

    // Well.. damn. Ignore this then.
    return null;
}


/*
 * Adds comment flags to a table.
 *
 * lines is an array of dictionaries grouping together comments on the
 * same line. The dictionaries contain the following keys:
 *
 *    text       - The text of the comment.
 *    line       - The first line number.
 *    num_lines  - The number of lines the comment spans.
 *    user       - A dictionary containing "username" and "name" keys
 *                 for the user.
 *    url        - The URL for the comment.
 *    localdraft - true if this is the current user's draft comment.
 *
 * @param {HTMLElement} table  The table to add flags to.
 * @param {object}      lines  The comment lines to add.
 * @param {string}      key    A unique ID identifying the file the comments
 *                             belong too (typically based on the filediff_id).
 */
function addCommentFlags(table, lines, key) {
    var remaining = {};

    var prevBeginRowIndex = undefined;

    for (var i in lines) {
        var line = lines[i];
        var numLines = line.num_lines;

        var beginLineNum = line.linenum;
        var endLineNum = beginLineNum + numLines - 1;
        var beginRow = findLineNumRow(table[0], beginLineNum,
                                      prevBeginRowIndex);

        if (beginRow != null) {
            prevBeginRowIndex = beginRow.rowIndex;

            var endRow = (endLineNum == beginLineNum
                          ? beginRow
                          : findLineNumRow(table[0], endLineNum,
                                           prevBeginRowIndex,
                                           prevBeginRowIndex + numLines - 1));


            /*
             * Note that endRow might be null if it exists in a collapsed
             * region, so we can get away with just using beginRow if we
             * need to.
             */
            new DiffCommentBlock($(beginRow), $(endRow || beginRow),
                                 beginLineNum, endLineNum, line.comments);
        } else {
            remaining[beginLineNum] = line;
        }
    }

    gHiddenComments[key] = remaining;
}


/*
 * Expands a chunk of the diff.
 *
 * @param {string} review_base_url     The URL of the review request.
 * @param {string} fileid              The file ID.
 * @param {string} filediff_id         The FileDiff ID.
 * @param {string} revision            The revision of the file.
 * @param {string} interdiff_revision  The interdiff revision of the file.
 * @param {int}    chunk_index         The chunk index number.
 * @param {string} lines_of_context    The string-based tuple of lines of
 *                                     context to show.
 * @param {string} link                The link triggering this call.
 */
RB.expandChunk = function(review_base_url, fileid, filediff_id, revision,
                          interdiff_revision, file_index, chunk_index,
                          lines_of_context, link) {
    gDiff.getDiffFragment(review_base_url, fileid, filediff_id, revision,
                          interdiff_revision, file_index, chunk_index,
                          lines_of_context,
                          function(html) {
        var tbody = $(link).parents('tbody'),
            table = tbody.parent(),
            key = 'file' + filediff_id,
            $scrollAnchor,
            tbodyID,
            scrollAnchorSel,
            scrollOffsetTop;

        /*
         * We want to position the new chunk or collapse button at roughly
         * the same position as the chunk or collapse button that the user
         * pressed. Figure out what it is exactly and what the scroll
         * offsets are so we can later reposition the scroll offset.
         */
        if ($(link).hasClass('diff-collapse-btn')) {
            $scrollAnchor = $(link);
        } else {
            $scrollAnchor = tbody;

            if (lines_of_context === 0) {
                /*
                 * We've expanded the entire chunk, so we'll be looking for
                 * the collapse button.
                 */
                tbodyID = /collapsed-(.*)/.exec($scrollAnchor[0].id)[1];
                tbodySel = 'img.diff-collapse-btn';
            } else {
                tbodyID = $scrollAnchor[0].id;
            }
        }

        scrollOffsetTop = $scrollAnchor.offset().top - $(window).scrollTop();

        /*
         * If we already expanded, we may have one or two loaded chunks
         * adjacent to the header. We want to remove those, since we'll be
         * generating new ones that include that data.
         */
        tbody.prev('.diff-header').remove();
        tbody.next('.diff-header').remove();
        tbody.prev('.loaded').remove();
        tbody.next('.loaded').remove();

        /*
         * Replace the header with the new HTML. This may also include a
         * new header.
         */
        tbody.replaceWith(html);
        addCommentFlags(table, gHiddenComments[key], key);

        /* Get the new tbody for the header, if any, and try to center. */
        if (tbodyID) {
            var el = document.getElementById(tbodyID);

            if (el) {
                $scrollAnchor = $(el);

                if (scrollAnchorSel) {
                    $scrollAnchor = $scrollAnchor.find(scrollAnchorSel);
                }

                if ($scrollAnchor.length > 0) {
                    $(window).scrollTop($scrollAnchor.offset().top -
                                        scrollOffsetTop);
                }
            }
        }

        /* Recompute the list of buttons for later use. */
        gCollapseButtons = $('table.sidebyside .diff-collapse-btn');
        updateCollapseButtonPos();

        /* The selection rectangle may not update -- bug #1353. */
        $(gAnchors[gSelectedAnchor]).highlightChunk();
    });
}


/*
 * Update the positions of the collapse buttons.
 *
 * This will attempt to position the collapse buttons such that they're
 * in the center of the exposed part of the expanded chunk in the current
 * viewport.
 *
 * As the user scrolls, they'll be able to see the button scroll along
 * with them. It will not, however, leave the confines of the expanded
 * chunk.
 */
function updateCollapseButtonPos() {
    var windowTop = $(window).scrollTop(),
        windowHeight = $(window).height(),
        len = gCollapseButtons.length,
        i;

    for (i = 0; i < len; i++) {
        var button = $(gCollapseButtons[i]),
            parentEl = button.parents('tbody'),
            parentOffset = parentEl.offset(),
            parentTop = parentOffset.top,
            parentHeight = parentEl.height(),
            btnRight = button.data('rb-orig-right');

        if (btnRight === undefined) {
            /*
             * We need to do this because on Firefox, the computed "right"
             * position will change when we move the element, causing things
             * to jump. We're really just trying to look up what the
             * default is, so do that once and cache.
             */
            btnRight = parseInt(button.css('right'), 10);
            button.data('rb-orig-right', btnRight);
        }

        /*
         * We're going to first try to limit our processing to expanded
         * chunks that are currently on the screen. We'll skip over any
         * before those chunks, and stop once we're sure we have no further
         * ones we can show.
         */
        if (parentTop >= windowTop + windowHeight) {
            /* We hit the last one, so we're done. */
            break;
        } else if (parentTop + parentHeight <= windowTop) {
            /* We're not there yet. */
        } else {
            var buttonHeight = button.outerHeight();

            /* Center the button in the view. */
            if (windowTop >= parentTop &&
                windowTop + windowHeight <= parentTop + parentHeight) {
                var btnParent = button.parent(),
                    parentLeft = btnParent.offset().left;

                /*
                 * Position this fixed in the center of the screen. It'll be
                 * less jumpy.
                 */
                button.css({
                    position: 'fixed',
                    left: parentLeft + btnParent.innerWidth() +
                          btnRight - parentOffset.left,
                    top: Math.round((windowHeight - buttonHeight) / 2)
                });

                /*
                 * Since the expanded chunk is taking up the whole screen,
                 * we have nothing else to process, so break.
                 */
                break;
            } else {
                var y1 = Math.max(windowTop, parentTop),
                    y2 = Math.min(windowTop + windowHeight,
                                  parentTop + parentHeight);

                /*
                 * The area doesn't take up the entire height of the
                 * view. Switch back to an absolute position.
                 */
                button.css({
                    position: 'absolute',
                    left: null,
                    top: y1 - parentTop +
                         Math.round((y2 - y1 - buttonHeight) / 2)
                });
            }
        }
    }
}


/*
 * Scrolls to the anchor at a specified location.
 *
 * @param {jQuery} anchor    The anchor jQuery instance.
 * @param {bool}   noscroll  true if the page should not be scrolled.
 *
 * @return {bool} true if the anchor was found, or false if not.
 */
function scrollToAnchor(anchor, noscroll) {
    if (anchor.length == 0) {
        return false;
    }

    if (anchor.parent().is(":hidden")) {
        return false;
    }

    if (!noscroll) {
        $(window).scrollTop(anchor.offset().top - DIFF_SCROLLDOWN_AMOUNT);
    }

    anchor.highlightChunk();

    for (var i = 0; i < gAnchors.length; i++) {
        if (gAnchors[i] == anchor[0]) {
            gSelectedAnchor = i;
            break;
        }
    }

    return true;
}


/*
 * Returns the next navigatable anchor in the specified direction.
 *
 * @param {int} dir         The direction (BACKWARD or FORWARD)
 * @param {int} anchorType  The type of the anchor as a bitmask
 *                          (ANCHOR_COMMENT, ANCHOR_FILE, ANCHOR_CHUNK)
 *
 * @return {jQuery} The found anchor jQuery instance, or INVALID.
 */
function GetNextAnchor(dir, anchorType) {
    for (var anchor = gSelectedAnchor + dir;
         anchor >= 0 && anchor < gAnchors.length;
         anchor = anchor + dir) {

        var anchorEl = $(gAnchors[anchor]);

        if (((anchorType & ANCHOR_COMMENT) &&
             anchorEl.hasClass("comment-anchor")) ||
            ((anchorType & ANCHOR_FILE) &&
             anchorEl.hasClass("file-anchor")) ||
            ((anchorType & ANCHOR_CHUNK) &&
             anchorEl.hasClass("chunk-anchor"))) {
            return anchorEl;
        }
    }

    return $([]);
}


/*
 * Updates the list of known anchors based on named anchors in the specified
 * table. This is called after every part of the diff that we loaded.
 *
 * If no anchor is selected, we'll try to select the first one.
 *
 * @param {jQuery} table  The table to load anchors from.
 */
function updateAnchors(table) {
    gAnchors = gAnchors.add($("a[name]", table));

    /* Skip over the change index to the first item */
    if (gSelectedAnchor == -1 && gAnchors.length > 0) {
      gSelectedAnchor = 0;
      $(gAnchors[gSelectedAnchor]).highlightChunk();
    }
}


/*
 * Progressively load a diff.
 *
 * When the diff is loaded, it will be placed into the appropriate location
 * in the diff viewer, rebuild the anchors, and move on to the next file.
 *
 * @param {string} review_base_url           The URL of the review request
 * @param {string} filediff_id               The filediff ID
 * @param {string} filediff_revision         The filediff revision
 * @param {string} interfilediff_id          The interfilediff ID (optional)
 * @param {string} interfilediff_revision    The interfilediff revision
 *                                           (optional)
 * @param {string} file_index                The file index
 * @param {dict}   comment_counts            The comments for this region
 */
RB.loadFileDiff = function(review_base_url, filediff_id, filediff_revision,
                           interfilediff_id, interfilediff_revision,
                           file_index, comment_counts) {
    if ($("#file" + filediff_id).length == 1) {
        /* We already have this one. This is probably a pre-loaded file. */
        setupFileDiff();
    } else {
        $.funcQueue("diff_files").add(function() {
            gDiff.getDiffFile(review_base_url, filediff_id, filediff_revision,
                              interfilediff_id, interfilediff_revision,
                              file_index, onFileLoaded);
        });
    }

    function onFileLoaded(xhr) {
        $("#file_container_" + filediff_id).replaceWith(xhr.responseText);

        setupFileDiff();
    }

    function setupFileDiff() {
        var key = "file" + filediff_id;

        gFileAnchorToId[key] = {
            'id': filediff_id,
            'revision': filediff_revision
        };

        if (interfilediff_id) {
            gInterdiffFileAnchorToId[key] = {
                'id': interfilediff_id,
                'revision': interfilediff_revision
            };
        }

        var diffTable = $("#file" + filediff_id);
        diffTable.diffFile(comment_counts, key);

        /* We must rebuild this every time. */
        updateAnchors(diffTable);

        if (gStartAtAnchor != null) {
            /* See if we've loaded the anchor the user wants to start at. */
            var anchor = $("a[name='" + gStartAtAnchor + "']");

            if (anchor.length != 0) {
                scrollToAnchor(anchor);
                gStartAtAnchor = null;
            }
        }

        $.funcQueue("diff_files").next();
    }
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

    gDiff = gReviewRequest.createDiff(gRevision, gInterdiffRevision);

    $(document).keypress(function(evt) {
        if (evt.altKey || evt.ctrlKey || evt.metaKey) {
            return;
        }

        var keyChar = String.fromCharCode(evt.which);

        for (var i = 0; i < gActions.length; i++) {
            if (gActions[i].keys.indexOf(keyChar) != -1) {
                gActions[i].onPress();
                return false;
            }
        }
    });

    $(window).scroll(updateCollapseButtonPos);
    $(window).resize(updateCollapseButtonPos);

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

    /* Check to see if there's an anchor we need to scroll to. */
    var url = document.location.toString();

    if (url.match("#")) {
        gStartAtAnchor = url.split("#")[1];
    }

    $.funcQueue("diff_files").start();

    $("table.sidebyside tr td a.moved-to," +
      "table.sidebyside tr td a.moved-from").click(function() {
        var destination = $(this).attr("line");

        return !scrollToAnchor(
            $("td a[target=" + destination + "]", $(this).parents("table"))
                .parent().siblings().andSelf()
                    .effect("highlight", {}, 2000), false);
    });
});

/**
 * The magic behind the "View revision:" buttons
 */
var diffHopper = new function() {
    var diffs = $('#jump_to_revision a.diff'),
        currentDiff,
        hideTimer = null,
        /**
         * Shows all the entries except the current selected
         */
        fixInterDiffForDisplay = function(revision) {
            $('#diffhopper_interdiff a').show();
            $('#diffhopper_interdiff_' + revision).hide();
        },
        /**
         * Hides the top and the bottom pickers
         */
        hide = function() {
            $('#diffhopper_diff').hide();
            $('#diffhopper_interdiff').hide();
            diffs.removeClass('hovered');
        }
    ;

    // These make up the public API
    return {
        hoverOver: function(revision) {
            currentDiff = revision;
            fixInterDiffForDisplay(revision);
            var revision_elem = diffs.eq(revision - 1),
              revision_offset = revision_elem.offset();
              centre = revision_offset.left + (revision_elem.outerWidth() / 2) - 1,
              diff_elem = $('#diffhopper_diff'),
              diff_width = diff_elem.outerWidth(),
              interdiff_width = $('#diffhopper_interdiff').outerWidth();

            diffs.removeClass('hovered');
            revision_elem.addClass('hovered');

            diff_elem.css({
                top: (revision_offset.top - diff_elem.outerHeight(true)) + 'px',
                left: (centre - diff_width / 2) + 'px',
                display: 'block'
            });

            $('#diffhopper_interdiff').css({
              top: (revision_offset.top + revision_elem.outerHeight()) + 'px',
              left: (centre - interdiff_width / 2) + 'px',
              display: 'block'
            });
        },
        startHideTimer: function() {
            hideTimer = window.setTimeout(hide, 500);
        },
        clearHideTimer: function() {
            window.clearTimeout(hideTimer);
        },
        hopToDiff: function(prefix, postfix) {
            location.href = prefix + currentDiff + postfix;
        },
        hopToInterDiff: function(otherDiff, prefix, postfix) {
            var leftDiff = Math.min(currentDiff, otherDiff),
              rightDiff = Math.max(currentDiff, otherDiff);
            location.href = prefix + leftDiff + '-' + rightDiff + postfix;
        }
    }
}();

// vim: set et:
