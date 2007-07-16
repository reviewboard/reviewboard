// Constants
var BACKWARD = -1;
var FORWARD  = 1;
var INVALID  = -1;
var DIFF_SCROLLDOWN_AMOUNT = 100;
var VISIBLE_CONTEXT_SIZE = 5;

var gLineCommentTmpl = new YAHOO.ext.DomHelper.Template(
    "<li class=\"comment\">" +
      "<dl>" +
        "<dt>" +
          "<a href=\"{user_url}\">{user_fullname}</a> " +
          "<span class=\"timestamp\">{timesince} ago.</span> " +
          "<span class=\"lines\">{lines}</span>" +
        "</dt>" +
        "<dd><pre>{text}</pre></dd>" +
      "</dl>" +
    "</li>");
gLineCommentTmpl.compile();

var gLineCommentDraftTmpl = new YAHOO.ext.DomHelper.Template(
    "<li class=\"comment draft\">" +
      "<dl>" +
        "<dt>" +
          "<label for=\"id_yourcomment\">" +
            "<a href=\"{user_url}\">{user_fullname}</a> " +
            "<span class=\"timestamp\">{timesince} ago.</span> " +
            "<span class=\"lines\">{lines}</span>" +
          "</label>" +
        "</dt>" +
        "<dd id=\"id_yourcomment\"><pre>{text}</pre></dd>" +
      "</dl>" +
    "</li>");
gLineCommentDraftTmpl.compile();

var gActions = [
    { // Previous file
        keys: "aAKP<m",
        onPress: function() { scrollToAnchor(GetNextFileAnchor(BACKWARD)); }
    },

    { // Next file
        keys: "fFJN>/",
        onPress: function() { scrollToAnchor(GetNextFileAnchor(FORWARD)); }
    },

    { // Previous diff
        keys: "sSkp,,",
        onPress: function() { scrollToAnchor(GetNextAnchor(BACKWARD)); }
    },

    { // Next diff
        keys: "dDjn..",
        onPress: function() { scrollToAnchor(GetNextAnchor(FORWARD)); }
    },

    { // Recenter
        keys: unescape("%0D"),
        onPress: function() { scrollToAnchor(gSelectedAnchor); }
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
var gCurrentAnchor = 0;
var gFileAnchorToId = {};
var gCommentDlg = null;
var gCommentBlocks = {};
var gHiddenComments = {};
var gGhostCommentFlag = null;
var gGhostCommentFlagRow = null;
var gSelection = {
    table: null,
    begin: null,
    beginNum: 0,
    end: null,
    endNum: 0,
    lastSeenIndex: 0
};

var dh = YAHOO.ext.DomHelper;


DiffCommentDialog = function(el) {
    DiffCommentDialog.superclass.constructor.call(this, el);
}


YAHOO.extendX(DiffCommentDialog, CommentDialog, {
    setCommentBlock: function(commentBlock) {
        if (this.commentBlock != commentBlock) {
            this.checkEmptyCommentBlock();
        }

        this.commentBlock = commentBlock;
        this.updateCommentsList();
        this.updateReviewCommentsList();
        this.newCommentField.dom.value = this.commentBlock.localComment;
        getEl('id_num_lines').dom.value = this.commentBlock.localNumLines;

        var commentLabel = getEl('id_comment_label');

        if (this.commentBlock.localNumLines == 1) {
            commentLabel.dom.innerHTML = "Your comment for line " +
                                        this.commentBlock.linenum;
        } else {
            commentLabel.dom.innerHTML = "Your comment for lines " +
                                         this.commentBlock.linenum + " - " +
                                         (this.commentBlock.linenum +
                                          this.commentBlock.localNumLines - 1);
        }
    },

    populateComments: function(rsp) {
        var ol = dh.overwrite(this.existingComments.dom, {
            tag: 'ol',
            id: 'comments-list'
        }, true);
        for (var commentnum in rsp.comments) {
            var comment = rsp.comments[commentnum];
            if (comment.num_lines == 1) {
                lines = "line " + comment.first_line;
            } else {
                lines = "lines " + comment.first_line + " - " +
                        (comment.num_lines + comment.first_line - 1);
            }

            var tmplData = {
                'user_url': comment.user.url,
                'lines': lines,
                'timesince': comment.timesince,
                'text': comment.text.htmlEncode().replace(/\n/g, "<br />"),
                'user_fullname': (comment.user.fullname != ""
                                  ? comment.user.fullname
                                  : comment.user.username)
            };

            if (comment.public) {
                gLineCommentTmpl.append(ol.dom, tmplData);
            } else {
                gLineCommentDraftTmpl.append(ol.dom, tmplData);
            }
        }
        this.updateCommentCount();

        var inlineCommentField = document.getElementById('id_yourcomment');
        if (inlineCommentField) {
            this.commentButtons[0].disable();
            if (this.commentBlock && this.commentBlock.hasDraft) {
                this.commentButtons[1].enable();
            } else {
                this.commentButtons[1].disable();
            }

            this.inlineEditor = new RB.widgets.InlineEditor({
                el: inlineCommentField,
                multiline: true,
                cls: 'inline-comment-editor',
                showEditIcon: true,
                stripTags: true,
                hideButtons: true
            });

            this.inlineEditor.on('beginedit', function(editor) {
                this.commentButtons[0].enable();
                if (this.commentBlock && this.commentBlock.hasDraft) {
                    this.commentButtons[1].enable();
                } else {
                    this.commentButtons[1].disable();
                }

                getEl(inlineCommentField).scrollIntoView(
                    this.commentsTab.bodyEl.dom.parentNode);
            }, this, true);

            this.commentForm.hide();
        } else {
            this.commentButtons[0].enable();
            this.commentButtons[1].disable();

            this.inlineEditor = null;
            this.commentForm.show();
        }

        this.onTabChanged();
    },

    resetReview: function(deleteDraft) {
        for (var id in gCommentBlocks) {
            var commentBlock = gCommentBlocks[id];

            if (commentBlock.hasDraft) {
                commentBlock.setHasDraft(false);

                if (deleteDraft) {
                    commentBlock.setCount(commentBlock.count - 1);
                }
            }

            commentBlock.localComment = "";
            commentBlock.localNumLines = 1;

            if (commentBlock.count == 0) {
                commentBlock.discard();
            }
        }

        this.commentBlock = null;
        this.bodyTop.el.dom.value = "";
        this.bodyBottom.el.dom.value = "";
        this.bodyTop.autoGrow();
        this.bodyBottom.autoGrow();
        getEl("id_shipit").dom.checked = false;
    },

    getCommentActionURL: function() {
        return this.getBaseURL() + '/diff/' + gRevision + '/file/' +
               this.commentBlock.filediffid + '/line/' +
               this.commentBlock.linenum + '/comments/';
    },

    closeDlg: function() {
        this.hide(this.checkEmptyCommentBlock.createDelegate(this));
		this.el.blur();
    },
});


CommentBlock = function(fileid, lineNumCell, linenum, comments) {
    this.discard = function() {
        delete gCommentBlocks[this.el.id];

        this.el.hide(true, .35, function() {
            this.el.remove();
        }.createDelegate(this));

        this.anchor.remove();
    };

    this.updatePosition = function() {
        this.el.setTop(getEl(this.lineNumCell).getY());
    };

    this.setCount = function(count) {
        this.count = count;
        this.el.dom.innerHTML = this.count;
    };

    this.setHasDraft = function(hasDraft) {
        if (hasDraft) {
            this.el.addClass("draft");
        } else {
            this.el.removeClass("draft");
        }

        this.hasDraft = hasDraft;
    };

    this.showCommentDlg = function() {
        if (gCommentDlg == null) {
            gCommentDlg = new DiffCommentDialog("comment-dlg");
        }

        gCommentDlg.setCommentBlock(this);
        if (gCommentDlg.isVisible()) {
            gCommentDlg.hide();
        }
        gCommentDlg.show(this.el);
    };

    this.fileid = fileid;
    this.filediffid = gFileAnchorToId[fileid];
    this.comments = comments;
    this.linenum = linenum;
    this.lineNumCell = lineNumCell;
    this.localComment = "";
    this.localNumLines = 1;
    this.hasDraft = false;

    this.el = dh.append(lineNumCell, {
        tag: 'span',
        cls: 'commentflag'
    }, true);

    this.anchor = dh.append(lineNumCell, {
        tag: 'a',
        name: 'file' + this.filediffid + 'line' + this.linenum
    }, true);

    for (comment in comments) {
        if (comments[comment].localdraft) {
            this.localComment = comments[comment].text;
            this.setHasDraft(true);
            break;
        }
    }

    this.updatePosition();
    this.el.on('click', function(e) {
        YAHOO.util.Event.stopEvent(e);
        this.showCommentDlg();
    }, this, true);

    this.setCount(comments.length);

    gCommentBlocks[this.el.id] = this;
};


function onKeyPress(evt) {
    var keyChar = String.fromCharCode(YAHOO.util.Event.getCharCode(evt));

    for (var i = 0; i < gActions.length; i++) {
        if (gActions[i].keys.indexOf(keyChar) != -1) {
            gActions[i].onPress();
            return;
        }
    }
}

function gotoAnchor(name, scroll) {
    return scrollToAnchor(GetAnchorByName(name), scroll || false);
}

function GetAnchorByName(name) {
    for (var anchor = 0; anchor < document.anchors.length; anchor++) {
        if (document.anchors[anchor].name == name) {
            return anchor;
        }
    }

    return INVALID;
}

function onPageLoaded(evt) {
    /* Skip over the change index to the first item */
    gSelectedAnchor = 1;
    SetHighlighted(gSelectedAnchor, true)

    YAHOO.util.Event.on(window, "keypress", onKeyPress);
    YAHOO.util.Event.on(window, "resize", onPageResize);
}

function onPageResize(evt) {
    for (var id in gCommentBlocks) {
        gCommentBlocks[id].updatePosition();
    }
}

function findLineNumCell(table, linenum) {
    var cell = null;
    var found = false;
    var row_offset = 1; // Get past the headers.

    if (table.rows.length - row_offset > linenum) {
        var norm_row = row_offset + linenum;
        var row = table.rows[row_offset + linenum];

        // Account for the "x lines hidden" row.
        if (row != null && row.cells.length > 3) {
            cell = (row.cells.length == 4 ? row.cells[1] : row.cells[0]);

            if (parseInt(cell.innerHTML) == linenum) {
                return cell;
            }
        }
    }

    /* Binary search for this cell. */
    var low = 1;
    var high = table.rows.length;

    if (cell != null) {
        /*
         * We collapsed the rows (unless someone mucked with the DB),
         * so the desired row is less than the row number retrieved.
         */
        high = parseInt(cell.innerHTML);
    }

    for (var i = Math.round((low + high) / 2); low < high - 1;) {
        var row = table.rows[row_offset + i];
        cell = (row.cells.length == 4 ? row.cells[1] : row.cells[0]);
        var value = parseInt(cell.innerHTML);

        if (!value) {
            i++;
            continue;
        }

        var oldHigh = high;
        var oldLow = low;

        if (value > linenum) {
            high = i;
        } else if (value < linenum) {
            low = i;
        } else {
            return cell;
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

function isLineNumCell(cell) {
    var content = cell.innerHTML;

    return (cell.tagName == "TH" &&
            cell.parentNode.parentNode.tagName == "TBODY" &&
            cell.className != "controls" && content != "..." &&
            parseInt(content) != NaN);
}

function onLineMouseDown(e, unused, table) {
    var node = e.target || e.srcElement;

    if (gGhostCommentFlagRow != null && node == gGhostCommentFlag.dom) {
        node = gGhostCommentFlagRow.dom;
    }

    if (isLineNumCell(node)) {
        YAHOO.util.Event.stopEvent(e);

        var row = node.parentNode;

        gSelection.table    = table;
        gSelection.begin    = gSelection.end    = node;
        gSelection.beginNum = gSelection.endNum = parseInt(node.innerHTML);
        gSelection.lastSeenIndex = row.rowIndex;
        getEl(row).addClass("selected");
    }
}

function onLineMouseUp(e, unused, table, fileid) {
    var node = e.target || e.srcElement;

    if (gGhostCommentFlag != null && node == gGhostCommentFlag.dom) {
        node = gGhostCommentFlagRow.dom;
    }

    if (isLineNumCell(node)) {
        YAHOO.util.Event.stopEvent(e);

        var commentBlock = new CommentBlock(fileid, gSelection.begin,
                                            gSelection.beginNum, []);
        commentBlock.localNumLines =
            gSelection.endNum - gSelection.beginNum + 1;

        var rows = gSelection.table.dom.rows;

        for (var i = gSelection.begin.parentNode.rowIndex;
             i <= gSelection.end.parentNode.rowIndex;
             i++) {

            getEl(rows[i]).removeClass("selected");
        }

        gSelection.begin    = gSelection.end    = null;
        gSelection.beginNum = gSelection.endNum = 0;
        gSelection.rows = [];
        gSelection.table = null;

        commentBlock.showCommentDlg();
    } else {
        var tbody = null;

        if (node.tagName == "PRE") {
            tbody = getEl(node.parentNode.parentNode.parentNode);
        } else if (node.tagName == "TD") {
            tbody = getEl(node.parentNode.parentNode);
        }

        if (tbody &&
            (tbody.hasClass("delete") || tbody.hasClass("insert") ||
             tbody.hasClass("replace"))) {
            gotoAnchor(tbody.dom.getElementsByTagName("A")[0].name, true);
        }
    }

    gGhostCommentFlagRow = null;
}

function onLineMouseOver(e, unused, table, fileid) {
    var node = getEl(e.target || e.srcElement);

    if (node.hasClass("commentflag")) {
        if (gGhostCommentFlag != null && node == gGhostCommentFlag.dom) {
            node = gGhostCommentFlagRow;
            getEl(node.dom.parentNode).addClass("selected");
        } else {
            node = getEl(node.dom.parentNode);
        }
    }

    if (isLineNumCell(node.dom)) {
        node.setStyle("cursor", "pointer");

        if (gSelection.table == table) {
            var linenum = parseInt(node.dom.innerHTML);

            if (linenum >= gSelection.beginNum) {
                var row = node.dom.parentNode;

                for (var i = gSelection.lastSeenIndex;
                     i <= row.rowIndex;
                     i++) {
                    getEl(table.dom.rows[i]).addClass("selected");
                }

                gSelection.end = node.dom;
                gSelection.endNum = linenum;
                gSelection.lastSeenIndex = row.rowIndex;
            }
        } else if (node.dom.childNodes.length == 1) {
            if (!gGhostCommentFlag) {
                gGhostCommentFlag = dh.append(document.body, {
                    id: 'ghost-commentflag',
                    tag: 'img',
                    src: '/images/comment-ghost.png'
                }, true);
                gGhostCommentFlag.enableDisplayMode();
                gGhostCommentFlag.setAbsolutePositioned();
                gGhostCommentFlag.setX(2);
            } else if (gGhostCommentFlagRow != null) {
                getEl(gGhostCommentFlagRow.dom.parentNode).removeClass("selected");
            }

            gGhostCommentFlag.setTop(node.getY() - 1);
            gGhostCommentFlag.show();
            gGhostCommentFlag.removeAllListeners();
            gGhostCommentFlag.on('mousedown',
                onLineMouseDown.createDelegate(this, [table], true));
            gGhostCommentFlag.on('mouseup',
                onLineMouseUp.createDelegate(this, [table, fileid], true));
            gGhostCommentFlag.on('mouseover',
                onLineMouseOver.createDelegate(this, [table, fileid], true));
            gGhostCommentFlagRow = node;

            getEl(node.dom.parentNode).addClass("selected");
        }
    } else if (gGhostCommentFlagRow != null && node != gGhostCommentFlagRow) {
        getEl(node.dom.parentNode).removeClass("selected");
    }
}

function onLineMouseOut(e, unused, table) {
    var relTarget = e.relatedTarget || e.toElement;
    if (gGhostCommentFlag && relTarget != gGhostCommentFlag.dom) {
        gGhostCommentFlag.hide();
    }

    if (gSelection.table == table) {
        var fromNode = getEl(e.originalTarget);

        if (fromNode.hasClass("commentflag")) {
            if (gGhostCommentFlag != null &&
                fromNode == gGhostCommentFlag.dom) {
                fromNode = gGhostCommentFlagRow;
            } else {
                fromNode = getEl(fromNode.dom.parentNode);
            }
        }

        if (isLineNumCell(relTarget)) {
            var destRowIndex = relTarget.parentNode.rowIndex;

            if (destRowIndex >= gSelection.begin.parentNode.rowIndex) {
				console.debug("mouse out. removing");
                for (var i = gSelection.lastSeenIndex;
                     i > relTarget.parentNode.rowIndex; i--) {
                    getEl(table.dom.rows[i]).removeClass("selected");
                }
            }
        }
    }
}

function addCommentFlags(fileid, table, lines) {
    var remaining = {};

    for (var linenum in lines) {
        linenum = parseInt(linenum);
        var cell = findLineNumCell(table.dom, linenum);

        if (cell != null) {
            new CommentBlock(fileid, cell, linenum, lines[linenum]);
        } else {
            remaining[linenum] = lines[linenum];
        }
    }

    gHiddenComments = remaining;
}

function addComments(fileid, lines) {
    var table = getEl(fileid);

    table.on('mousedown', onLineMouseDown.createDelegate(this, [table], true));
    table.on('mouseup', onLineMouseUp.createDelegate(this, [table, fileid],
                                                     true));
    table.on('mouseover', onLineMouseOver.createDelegate(this, [table, fileid],
                                                         true));
    table.on('mouseout', onLineMouseOut.createDelegate(this, [table], true));

    addCommentFlags(fileid, table, lines);
}

function expandChunk(fileid, filediff_id, chunk_index, tbody_id) {
    var url = '/r/' + gReviewRequestId + '/diff/' + gRevision +
              '/fragment/' + filediff_id + '/chunk/' + chunk_index + '/';
    YAHOO.util.Connect.asyncRequest("GET", url, {
        success: function(res) {
            var tbody = getEl(tbody_id);
            var table = getEl(tbody.dom.parentNode);
            var el = dh.insertHtml("afterEnd", tbody.dom, res.responseText);
            tbody.remove();

            addCommentFlags(fileid, table, gHiddenComments);
            onPageResize(); // Make sure we update the flag positions.
        }
    });
}

function scrollToAnchor(anchor, noscroll) {
    if (anchor == INVALID) {
        return false;
    }

    if (!noscroll) {
        window.scrollTo(0, getEl(document.anchors[anchor]).getY() -
                           DIFF_SCROLLDOWN_AMOUNT);
    }

    SetHighlighted(gSelectedAnchor, false);
    SetHighlighted(anchor, true);
    gSelectedAnchor = anchor;

    return true;
}

function GetNextAnchor(dir) {
    for (var anchor = gSelectedAnchor + dir; ; anchor = anchor + dir) {
        if (anchor < 0 || anchor >= document.anchors.length) {
            return INVALID;
        }

        var name = document.anchors[anchor].name;

        if (name == "index_header" || name == "index_footer") {
            return INVALID;
        } else if (name.substr(0, 4) != "file") {
            return anchor;
        }
    }
}

function GetNextFileAnchor(dir) {
    var fileId = document.anchors[gSelectedAnchor].name.split(".")[0];
    var newAnchor = parseInt(fileId) + dir;
    return GetAnchorByName(newAnchor);
}

function SetHighlighted(anchor, highlighted) {
    var anchorNode = document.anchors[anchor];
    var nextNode = anchorNode.nextSibling.nextSibling;
    var controlsNode;

    if (anchorNode.parentNode.tagName == "TH") {
        controlsNode = anchorNode;
    } else if (nextNode.className == "sidebyside") {
        controlsNode = nextNode.rows[0].cells[0];
    } else {
        return;
    }

    controlsNode.textContent = (highlighted ? "▶" : "");
}

function addAnchorMapping(name, id) {
    gFileAnchorToId[name] = id;
}

YAHOO.util.Event.on(window, "load", onPageLoaded);
