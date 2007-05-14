// Comments
var gReviewCommentTmpl = new YAHOO.ext.DomHelper.Template(
    "<li class=\"comment\">" +
      "<dl>" +
        "<dt>" +
          "<span class=\"filename\">{filename}</span> " +
          "<span class=\"lines\">{lines}</span>" +
        "</dt>" +
        "<dd>{text}</dd>" +
      "</dl>" +
    "</li>");
gReviewCommentTmpl.compile();


var dh = YAHOO.ext.DomHelper;


CommentDialog = function(el) {
    CommentDialog.superclass.constructor.call(this, el, {
        width: 550,
        height: 450,
        shadow: true,
        minWidth: 400,
        minHeight: 300,
        autoTabs: true,
        proxyDrag: true,
        constraintoviewport: false,
        fixedcenter: false
    });

    var tabs = this.getTabs();

    /*
     * Global Dialog
     */
    this.addKeyListener(27, this.closeDlg, this);
    this.setDefaultButton(this.addButton("Close", this.closeDlg, this));
    this.messageDiv = dh.insertBefore(this.footer.dom,
        {tag: 'div', id: 'comment-status'}, true);

    /* Prevent navigation keypresses in the comments textarea. */
    this.el.on("keypress", function(e) {
        YAHOO.util.Event.stopPropagation(e);
    }, this, true);

    tabs.on('tabchange', this.onTabChanged, this, true);

    this.on('resize', this.onDlgResize, this, true);
    this.on('show', function() {
        if (this.commentForm.isVisible()) {
            this.newCommentField.focus();
        }
    }, this, true);

    this.on('beforeshow', function() {
        this.xy = this.el.getCenterXY(true);
        this.xy[0] -= Math.round(this.size.width / 2);

        if (this.xy[0] < 60) {
            this.xy[0] = 60;
        }
    }, this, true);


    /*
     * Comments Tab
     */
    this.commentsTab = tabs.getTab("tab-comments");
    this.commentForm = getEl('commentform');
    this.commentForm.enableDisplayMode();

    this.newCommentField = getEl('id_comment');
    this.commentActionField = getEl('id_comment_action');
    this.existingComments = getEl('existing-comments');
    this.inlineEditor = null;

    this.commentButtons = [
        this.addButton("Save Comment", this.postComment, this),
        this.addButton("Delete Comment", this.deleteComment, this)
    ];


    /*
     * Review Tab
     */
    this.reviewTab = tabs.getTab("tab-review");

    this.reviewForm = getEl('reviewform');

    this.reviewButtons = [
        this.addButton("Save Draft", this.saveReview, this),
        this.addButton("Delete Draft", this.deleteReview, this),
        this.addButton("Publish", this.publishReview, this)
    ];

    this.bodyTop = new RB.widgets.AutosizeTextArea('id_body_top', {
        autoGrowVertical: true
    });
    this.bodyBottom = new RB.widgets.AutosizeTextArea('id_body_bottom', {
        autoGrowVertical: true
    });


    /*
     * Set this here instead of in the CSS to work around a visual glitch
     * the first time this dialog is shown.
     */
    this.reviewBody = getEl('review-body');
    this.reviewBody.setStyle('overflow', 'auto');
    this.reviewBody.on('click', function(e) {
        if ((e.target || e.srcElement) == this.reviewBody.dom) {
            this.bodyBottom.el.focus()
        }
    }, this, true);


    /*
     * Set the initial state
     */
    this.onTabChanged();
}


YAHOO.extendX(CommentDialog, YAHOO.ext.BasicDialog, {
    onDlgResize: function() {
        if (this.inlineEditor) {
            this.alignFieldToBottomRight(this.commentsTab,
                                         this.inlineEditor.field, 100);
        } else {
            this.alignFieldToBottomRight(
                this.commentsTab, this.newCommentField,
                (this.commentBlock && this.commentBlock.count == 0
                 ? null : 100));
        }

        this.alignFieldToBottomRight(this.reviewTab, this.reviewBody);
    },

    onTabChanged: function() {
        var activeTab = this.getTabs().getActiveTab();
        var bodyParent = getEl(this.reviewTab.bodyEl.dom.parentNode);

        this.hideMessage();

        if (activeTab == this.commentsTab) {
            for (b in this.commentButtons) { this.commentButtons[b].show(); }
            for (b in this.reviewButtons)  { this.reviewButtons[b].hide(); }
            bodyParent.setStyle("overflow-y", "auto");
            bodyParent.setStyle("overflow-x", "hidden");
            //this.scrollToBottom();
        } else if (activeTab == this.reviewTab) {
            for (b in this.commentButtons) { this.commentButtons[b].hide(); }
            for (b in this.reviewButtons)  { this.reviewButtons[b].show(); }
            this.reviewTab.bodyEl.dom.parentNode.scrollTop = 0;
            bodyParent.setStyle("overflow", "hidden");
            //this.bodyTop.el.focus();
        }

        this.onDlgResize();

        if (activeTab == this.commentsTab) {
            this.scrollToBottom();
        }
    },

    alignFieldToBottomRight: function(tab, el, forcedHeight) {
        var container = getEl(tab.bodyEl.dom.parentNode);
        var newHeight;

        container.beginMeasure();

        if (forcedHeight) {
            newHeight = forcedHeight;
        } else {
            newHeight = container.getHeight() -
                        el.dom.offsetTop -
                        tab.bodyEl.getPadding("tb") -
                        tab.bodyEl.getBorderWidth("tb");
        }

        el.setSize(container.dom.clientWidth -
                   tab.bodyEl.getPadding("lr") -
                   tab.bodyEl.getBorderWidth("lr"),
                   newHeight);
        container.endMeasure();
    },

    getBaseURL: function() {
        return '/api/json/reviewrequests/' + gReviewRequestId;
    },

    getReviewActionURL: function() {
        return this.getBaseURL() + '/reviews/draft/';
    },

    fillReviewCommentsList: function(rsp) {
        var el = document.getElementById('all-review-comments');

        if (rsp.comments.length == 0 && rsp.screenshot_comments.length == 0) {
            dh.overwrite(el, {
                tag: 'i',
                html: 'All Comments, if any, will be displayed here once added.'
            });
        } else {
            var ol = dh.overwrite(el, {tag: 'ol'}, true);
            for (var commentnum in rsp.screenshot_comments) {
                var comment = rsp.screenshot_comments[commentnum];
                gReviewCommentTmpl.append(ol.dom, {
                    'filename': comment.screenshot.title,
                    'text': comment.text.htmlEncode().replace(/\n/g, "<br />")
                });
            }
            for (var commentnum in rsp.comments) {
                var comment = rsp.comments[commentnum];
                if (comment.num_lines == 1) {
                    lines = "line " + comment.first_line;
                } else {
                    lines = "lines " + comment.first_line + " - " +
                            (comment.num_lines + comment.first_line - 1);
                }
                gReviewCommentTmpl.append(ol.dom, {
                    'filename': comment.filediff.source_file,
                    'lines': lines,
                    'text': comment.text.htmlEncode().replace(/\n/g, "<br />")
                });
            }
        }
    },

    checkEmptyCommentBlock: function() {
        if (this.commentBlock && this.commentBlock.count == 0) {
            var commentBlock = this.commentBlock;
            this.commentBlock = null;
            commentBlock.discard();
        }
    },

    scrollToBottom: function() {
        var scrollNode = this.commentsTab.bodyEl.dom.parentNode;
        scrollNode.scrollTop = scrollNode.scrollHeight;
    },

    updateCommentCount: function() {
        var count = this.existingComments.getChildrenByClassName("comment",
                                                                 "li").length;
        this.commentBlock.setCount(count);
        this.commentsTab.setText("Comments (" + count + ")");
    },

    postComment: function() {
        if (this.inlineEditor) {
            this.newCommentField.dom.value = this.inlineEditor.getValue();
            this.inlineEditor.completeEdit();
        }

        var text = this.newCommentField.dom.value;

        if (text.strip() == "") {
            this.showError("Please fill out the comment text.");
            return;
        }

        this.commentAction("set", function(rsp) {
            this.commentBlock.setHasDraft(true);
            this.populateComments(rsp);
            this.updateReviewCommentsList();
        }.createDelegate(this));
    },

    deleteComment: function() {
        this.commentAction("delete", function(rsp) {
            this.commentBlock.setHasDraft(false);
            this.newCommentField.dom.value = "";
            this.populateComments(rsp);
            this.updateCommentCount();
            this.closeDlg();
        }.createDelegate(this));
    },

    saveReview: function() {
        this.reviewAction("save",
            this.checkEmptyCommentBlock.createDelegate(this));
    },

    deleteReview: function() {
        this.reviewAction("delete",
            this.resetReview.createDelegate(this, [true]));
    },

    publishReview: function() {
        this.reviewAction("publish", this.resetReview.createDelegate(this));
    },

    showError: function(text) {
        this.showMessage(text, "error");
    },

    reviewAction: function(action, onSuccess) {
        YAHOO.util.Connect.setForm(this.reviewForm.dom);
        YAHOO.util.Connect.asyncRequest(
            "POST", this.getReviewActionURL() + action + '/', {
            success: function(res) {
                this.hideMessage();
                this.hide(onSuccess);
            }.createDelegate(this),

            failure: function(res) {
                this.showError(res.statusText);
            }.createDelegate(this)
        });
    },

    showMessage: function(message, className) {
        this.messageDiv.dom.innerHTML = message

        if (className) {
            this.messageDiv.dom.className = className;
        }

        this.messageDiv.show();
    },

    hideMessage: function() {
        this.messageDiv.dom.className = "";
        this.messageDiv.hide();
    },

    commentAction: function(action, onSuccess) {
        this.commentActionField.dom.value = action;

        YAHOO.util.Connect.setForm(this.commentForm.dom);
        asyncJsonRequest("POST", this.getCommentActionURL(), {
            success: function(rsp) {
                this.hideMessage();
                this.commentBlock.localComment = "";
                onSuccess(rsp);
            }.createDelegate(this),

            failure: function(errmsg, rsp) {
                this.showError(errmsg);
            }.createDelegate(this)
        });
    },

    updateCommentsList: function() {
        asyncJsonRequest("GET", this.getCommentActionURL(), {
            success: function(rsp) {
                this.hideMessage();
                this.populateComments(rsp);
            }.createDelegate(this),

            failure: function(errmsg) {
                this.showError(errmsg);
            }.createDelegate(this)
        });
    },

    updateReviewCommentsList: function() {
        asyncJsonRequest("GET",
                         this.getReviewActionURL() +
                         "comments/?diff_revision=" + gRevision, {
            success: this.fillReviewCommentsList.createDelegate(this),
            failure: function(errmsg, rsp) {
                getEl('all-review-comments').dom.innerHTML =
                    "<b>Error:</b> Unable to retrieve list of comments: " +
                    errmsg;
            }.createDelegate(this)
        });
    },
});
