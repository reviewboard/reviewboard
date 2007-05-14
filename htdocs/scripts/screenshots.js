// Constants
var gRegionCommentTmpl = new YAHOO.ext.DomHelper.Template(
    "<li class=\"comment\">" +
      "<dl>" +
        "<dt>" +
          "<a href=\"{user_url}\">{user_fullname}</a> " +
          "<span class=\"timestamp\">{timesince} ago.</span>" +
        "</dt>" +
        "<dd>{text}</dd>" +
      "</dl>" +
    "</li>");
gRegionCommentTmpl.compile();

var gRegionCommentDraftTmpl = new YAHOO.ext.DomHelper.Template(
    "<li class=\"comment draft\">" +
      "<dl>" +
        "<dt>" +
          "<label for=\"id_yourcomment\">" +
            "<a href=\"{user_url}\">{user_fullname}</a> " +
            "<span class=\"timestamp\">{timesince} ago.</span>" +
          "</label>" +
        "</dt>" +
        "<dd id=\"id_yourcomment\">{text}</dd>" +
      "</dl>" +
    "</li>");
gRegionCommentDraftTmpl.compile();

// State variables
var gCommentDlg = null;
var gCommentBlocks = {};
var gSelectionSensitive = true;
var gSelection = {
    image: null,
    beginX: -1,
    beginY: -1,
    endX: -1,
    endY: -1
};
var dh = YAHOO.ext.DomHelper;


ScreenshotCommentDialog = function(el) {
    ScreenshotCommentDialog.superclass.constructor.call(this, el);
}

YAHOO.extendX(ScreenshotCommentDialog, CommentDialog, {
    setCommentBlock: function(commentBlock) {
        if (this.commentBlock != commentBlock) {
            this.checkEmptyCommentBlock();
        }

        this.commentBlock = commentBlock;

        this.updateCommentsList();
        this.updateReviewCommentsList();

        var commentLabel = getEl('id_comment_label');

        // FIXME: it'd be nice to show something more useful here.
        commentLabel.dom.innertHTML = "Your comment for selected region";
    },

    populateComments: function(rsp) {
        var ol = dh.overwrite(this.existingComments.dom, {
            tag: 'ol',
            id: 'comments-list'
        }, true);
        for (var commentnum in rsp.comments) {
            var comment = rsp.comments[commentnum];

            var tmplData = {
                'user_url': comment.user.url,
                'timesince': comment.timesince,
                'text': comment.text.htmlEncode().replace(/\n/g, "<br />"),
                'user_fullname': (comment.user.fullname != ""
                                  ? comment.user.fullname
                                  : comment.user.username)
            };

            if (comment.public) {
                gRegionCommentTmpl.append(ol.dom, tmplData);
            } else {
                gRegionCommentDraftTmpl.append(ol.dom, tmplData);
            }
        }
        this.updateCommentCount();

        var inlineCommentField = document.getElementById('id_yourcomment');
        if (inlineCommentField) {
            for (b in this.commentButtons) {
                this.commentButtons[b].disable();
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
                for (b in this.commentBUttons) {
                    this.commentButtons[b].enable();
                }

                getEl(inlineCommentField).scrollIntoView(
                    this.commentsTab.bodyEl.dom.parentNode);
            }, this, true);

            this.commentForm.hide();
        } else {
            for (b in this.commentButtons) {
                this.commentButtons[b].enable();
            }

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
            commentBlock.beginX = -1;
            commentBlock.beginY = -1;

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
        return this.getBaseURL() + '/s/' + gScreenshotId + '/comments/' +
               this.commentBlock.w + 'x' + this.commentBlock.h + '+' +
               this.commentBlock.x + '+' + this.commentBlock.y + '/';
    },

    closeDlg: function() {
        this.hide(this.checkEmptyCommentBlock.createDelegate(this));
        gSelectionSensitive = true;
    },
});


CommentBlock = function(x, y, w, h, container, comments) {
    this.discard = function() {
        delete gCommentBlocks[this.el.id];

        this.el.hide(true, .35, function() {
            this.el.remove();
        }.createDelegate(this));
    };

    this.updatePosition = function() {
        var image = getEl("screenshot-display").dom.firstChild;
        var imageX = YAHOO.util.Dom.getX(image);
        var imageY = YAHOO.util.Dom.getY(image);

        var style = this.el.dom.style;
        style.left = (this.x + imageX) + "px";
        style.top  = (this.y + imageY) + "px";
        style.width  = this.w + "px";
        style.height = this.h + "px";
    };

    this.setCount = function(count) {
        this.count = count;
        this.flag.dom.innerHTML = this.count;
    };

    this.setHasDraft = function(hasDraft) {
        if (hasDraft) {
            this.el.addClass("draft");
            this.flag.addClass('draft');
        } else {
            this.el.removeClass("draft");
            this.flag.removeClass('draft');
        }

        this.hasDraft = hasDraft;
    };

    this.showCommentDlg = function() {
        if (gCommentDlg == null) {
            gCommentDlg = new ScreenshotCommentDialog("comment-dlg");
        }

        gCommentDlg.setCommentBlock(this);
        gCommentDlg.show(this.el);
        gSelectionSensitive = false;
    };

    this.comments = comments;
    this.localComment = "";
    this.hasDraft = false;
    this.x = x;
    this.y = y;
    this.w = w;
    this.h = h;

    this.el = dh.append(container.dom, {
        tag: 'div',
        cls: 'selection'
    }, true);

    this.flag = dh.append(this.el.dom, {
        tag: 'div',
        cls: 'selection-flag'
    }, true);

    for (comment in comments) {
        if (comments[comment].localdraft) {
            this.localComment = comments[comment].text;
            this.setHasDraft(true);
            break;
        }
    }

    this.updatePosition();

    this.flag.on('click', function(e) {
        YAHOO.util.Event.stopEvent(e);
        this.showCommentDlg();
    }, this, true);

    this.setCount(comments.length);
    gCommentBlocks[this.el.id] = this;
}


function getRelativeXY(e, relativeEl) {
    var result = new Array();

    var relativeX = YAHOO.util.Dom.getX(relativeEl);
    var relativeY = YAHOO.util.Dom.getY(relativeEl);

    var x = e.clientX + window.pageXOffset -
            relativeX;
    var y = e.clientY + window.pageYOffset -
            relativeY;

    if (x < 0) x = 0;
    if (y < 0) y = 0;
    if (x > relativeEl.width)  x = relativeEl.width;
    if (y > relativeEl.height) y = relativeEl.height;

    result[0] = x;
    result[1] = y;
    result[2] = relativeX;
    result[3] = relativeY;
    return result;
}


function addComments(regions) {
    var container = getEl("screenshot-display");
    var image = container.dom.firstChild;
    var selection = dh.append(container.dom, {
        tag: 'div',
        id: 'selection-interactive'
    }, true);
    var selections = dh.append(container.dom, {
        tag: 'div',
        id: 'selection-container'
    }, true);

    container.on('mousedown', function(e) {
        if (gSelectionSensitive == false) {
            return;
        }

        if (e.button == 0 && gSelection.image == null) {
            YAHOO.util.Event.stopEvent(e);

            var position = getRelativeXY(e, image);

            gSelection.beginX = position[0];
            gSelection.beginY = position[1];
            gSelection.endX = position[0];
            gSelection.endy = position[1];
            gSelection.image = image;

            var style = selection.dom.style;
            style.left = (position[0] + position[2]) + "px";
            style.top  = (position[1] + position[3]) + "px";
            style.width = "0px";
            style.height = "0px";
            style.visibility = "visible";
        }
    });

    container.on('mouseup', function(e) {
        if (gSelectionSensitive == false) {
            return;
        }

        if (gSelection.image) {
            YAHOO.util.Event.stopEvent(e);
            var position = getRelativeXY(e, image);
            var x = position[0];
            var y = position[1];

            if (x < gSelection.beginX) {
                gSelection.endX = gSelection.beginX;
                gSelection.beginX = x;
            } else {
                gSelection.endX = x;
            }

            if (y < gSelection.beginY) {
                gSelection.endY = gSelection.beginY;
                gSelection.beginY = y;
            } else {
                gSelection.endY = y;
            }

            selection.dom.style.visibility = "hidden";

            var w = gSelection.endX - gSelection.beginX;
            var h = gSelection.endY - gSelection.beginY;

            /*
             * If we don't pass an arbitrary minimum size threshold, don't do
             * anything.  This helps avoid making people mad if they
             * accidentally click on the image.
             */
            if (w > 5 && h > 5) {
                var commentBlock = new CommentBlock(gSelection.beginX,
                                                    gSelection.beginY,
                                                    w, h, selections, []);
                commentBlock.showCommentDlg();

            }
            gSelection.image = null;
        }
    });


    container.on('mousemove', function(e) {
        if (gSelectionSensitive == false) {
            return;
        }

        if (gSelection.image) {
            YAHOO.util.Event.stopEvent(e);

            var position = getRelativeXY(e, image);

            if (gSelection.beginX <= position[0]) {
                selection.dom.style.left = (gSelection.beginX +
                                            position[2]) + "px";
                selection.dom.style.width = position[0] -
                                            gSelection.beginX +
                                            "px";
            } else {
                selection.dom.style.left = (position[0] +
                                            position[2]) + "px";
                selection.dom.style.width = gSelection.beginX -
                                            position[0] + "px";
            }

            if (gSelection.beginY <= position[1]) {
                selection.dom.style.top = (gSelection.beginY +
                                           position[3]) + "px";
                selection.dom.style.height = position[1] -
                                             gSelection.beginY +
                                             "px";
            } else {
                selection.dom.style.top = (position[1] +
                                           position[3]) + "px";
                selection.dom.style.height = gSelection.beginY -
                                             position[1] + "px";
            }
        }
    });

    container.on('mouseover', function(e) {
        selections.dom.style.visibility = 'visible';
    });

    container.on('mouseout', function(e) {
        selections.dom.style.visibility = 'hidden';
    });

    for (region in regions) {
        var comments = regions[region];
        var x = comments[0].x;
        var y = comments[0].y;
        var w = comments[0].w;
        var h = comments[0].h;

        new CommentBlock(x, y, w, h, selections, comments);
    }
}

function onPageLoaded(evt) {
    YAHOO.util.Event.on(window, 'resize', onPageResize);
}

function onPageResize(evt) {
    for (var id in gCommentBlocks) {
        gCommentBlocks[id].updatePosition();
    }
}

YAHOO.util.Event.on(window, "load", onPageLoaded);
