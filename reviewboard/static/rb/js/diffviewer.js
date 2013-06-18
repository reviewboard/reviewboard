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
var gCollapseButtons = [];


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
 * Registers a section as being a diff file.
 *
 * This handles all mouse actions on the diff, comment range selection, and
 * populatation of comment flags.
 *
 * @return {jQuery} The diff file element.
 */
$.fn.diffFile = function(diffReviewable, lines, key) {
    return this.each(function() {
        var self = $(this),
            diffReviewableView = new RB.DiffReviewableView({
                el: self,
                model: diffReviewable
            });

        self.data('diffReviewableView', diffReviewableView);

        addCommentFlags(diffReviewableView, self, lines, key);

        diffReviewableView.render();
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
 * Adds comment flags to a table.
 *
 * lines is an array of dictionaries grouping together comments on the
 * same line. The dictionaries contain the following keys:
 */
function addCommentFlags(diffReviewableView, table, lines, key) {
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
    var tbody = $(link).parents('tbody'),
        table = tbody.parent(),
        diffReviewableView = table.data('diffReviewableView');

    diffReviewableView.model.getRenderedDiffFragment({
        reviewRequestURL: review_base_url,
        fileDiffID: filediff_id,
        revision: revision,
        interdiffRevision: interdiff_revision,
        fileIndex: file_index,
        chunkIndex: chunk_index,
        linesOfContext: lines_of_context,
    }, {
        success: function(html) {
            var key = 'file' + filediff_id,
                $scrollAnchor,
                tbodyID,
                scrollAnchorSel,
                scrollOffsetTop;

            /*
             * We want to position the new chunk or collapse button at
             * roughly the same position as the chunk or collapse button
             * that the user pressed. Figure out what it is exactly and what
             * the scroll offsets are so we can later reposition the scroll
             * offset.
             */
            if ($(link).hasClass('diff-collapse-btn')) {
                $scrollAnchor = $(link);
            } else {
                $scrollAnchor = tbody;

                if (lines_of_context === 0) {
                    /*
                     * We've expanded the entire chunk, so we'll be looking
                     * for the collapse button.
                     */
                    tbodyID = /collapsed-(.*)/.exec($scrollAnchor[0].id)[1];
                    tbodySel = 'img.diff-collapse-btn';
                } else {
                    tbodyID = $scrollAnchor[0].id;
                }
            }

            scrollOffsetTop = $scrollAnchor.offset().top -
                              $(window).scrollTop();

            /*
             * If we already expanded, we may have one or two loaded chunks
             * adjacent to the header. We want to remove those, since we'll
             * be generating new ones that include that data.
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
            addCommentFlags(diffReviewableView, table, gHiddenComments[key],
                            key);

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
        }
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

RB.scrollToAnchor = scrollToAnchor;


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
    var diffReviewable = new RB.DiffReviewable({
        reviewRequestURL: review_base_url,
        fileDiffID: filediff_id,
        interFileDiffID: interfilediff_id,
        revision: filediff_revision,
        interdiffRevision: interfilediff_revision
    });

    if ($("#file" + filediff_id).length == 1) {
        /* We already have this one. This is probably a pre-loaded file. */
        setupFileDiff();
    } else {
        $.funcQueue("diff_files").add(function() {
            diffReviewable.getRenderedDiff({
                fileIndex: file_index
            }, {
                complete: onFileLoaded
            });
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
        diffTable.diffFile(diffReviewable, comment_counts, key);

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

// vim: set et:
