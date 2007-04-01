// Constants
var BACKWARD = -1;
var FORWARD  = 1;
var INVALID  = -1;
var DIFF_SCROLLDOWN_AMOUNT = 100;
var VISIBLE_CONTEXT_SIZE = 5;

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
var gGhostCommentFlag = null;
var gSelection = {
	table: null,
	begin: null,
	beginNum: 0,
	end: null,
	endNum: 0,
	lastSeenIndex: 0
};

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
		fixedcenter: true
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
	closeDlg: function() {
		this.hide(this.checkEmptyCommentBlock.createDelegate(this));
	},

	checkEmptyCommentBlock: function() {
		if (this.commentBlock && this.commentBlock.count == 0) {
			var commentBlock = this.commentBlock;
			this.commentBlock = null;
			commentBlock.discard();
		}
	},

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

	updateCommentsList: function() {
		YAHOO.util.Connect.asyncRequest("GET", this.getCommentActionURL(), {
			success: function(res) {
				this.hideMessage();
				this.populateComments(res.responseText);
			}.createDelegate(this),

			failure: function(res) {
				this.showError(res.statusText);
			}.createDelegate(this)
		});
	},

	updateReviewCommentsList: function() {
		YAHOO.util.Connect.asyncRequest(
			"GET", this.getReviewActionURL() + "comments/", {

			success: function(res) {
				getEl('all-review-comments').dom.innerHTML = res.responseText;
			}.createDelegate(this),

			failure: function(res) {
				getEl('all-review-comments').dom.innerHTML =
					"<b>Error:</b> Unable to retrieve list of comments: " +
					res.statusText;
			}.createDelegate(this)
		});
	},

	populateComments: function(html) {
		this.existingComments.dom.innerHTML = html;
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
				for (b in this.commentButtons) {
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

		this.commentAction("set", function(res) {
			this.commentBlock.setHasDraft(true);
			this.populateComments(res.responseText);
			this.updateReviewCommentsList();
		}.createDelegate(this));
	},

	deleteComment: function() {
		this.commentAction("delete", function(res) {
			this.commentBlock.setHasDraft(false);
			this.newCommentField.dom.value = "";
			this.existingComments.dom.innerHTML = res.responseText;
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

	showError: function(text) {
		this.showMessage(text, "error");
	},

	getCommentActionURL: function() {
		return "comments/" + this.commentBlock.filediffid + "/" +
		       this.commentBlock.linenum + "/";
	},

	getReviewActionURL: function() {
		return gReviewRequestPath + "replies/" + gRevision + "/";
	},

	commentAction: function(action, onSuccess) {
		this.commentActionField.dom.value = action;

		YAHOO.util.Connect.setForm(this.commentForm.dom);
		YAHOO.util.Connect.asyncRequest("POST", this.getCommentActionURL(), {
			success: function(res) {
				this.hideMessage();
				this.commentBlock.localComment = "";
				onSuccess(res);
			}.createDelegate(this),

			failure: function(res) {
				this.showError(res.statusText);
			}.createDelegate(this)
		});
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
	}
});


CommentBlock = function(fileid, lineNumCell, linenum, comments) {
	this.discard = function() {
		delete gCommentBlocks[this.el.id];

		this.el.hide(true, .35, function() {
			this.el.remove();
		}.createDelegate(this));
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
			gCommentDlg = new CommentDialog("comment-dlg");
		}

		gCommentDlg.setCommentBlock(this);
		gCommentDlg.show(this.el);
	};

	this.fileid = fileid;
	this.filediffid = gFileAnchorToId[fileid];
	this.comments = comments;
	this.linenum = linenum;
	this.localComment = "";
	this.localNumLines = 1;
	this.hasDraft = false;

	this.el = dh.append(lineNumCell, {
		tag: 'span',
		cls: 'commentflag'
	}, true);

	for (comment in comments) {
		if (comments[comment].localdraft) {
			this.localComment = comments[comment].text;
			this.setHasDraft(true);
			break;
		}
	}

	this.el.setTop(getEl(lineNumCell).getY());
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

function gotoAnchor(name) {
	return scrollToAnchor(GetAnchorByName(name));
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

	for (var i = Math.round((low + high) / 2);
	     low < high - 1;) {
		var row = table.rows[row_offset + i];
		cell = (row.cells.length == 4 ? row.cells[1] : row.cells[0]);
		var value = parseInt(cell.innerHTML);

		if (!value) {
			i++;
			continue;
		}

		if (value > linenum) {
			high = i;
		} else if (value < linenum) {
			low = i;
		} else {
			return cell;
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

function addComments(fileid, lines) {
	var table = getEl(fileid);

	table.on('mousedown', function(e) {
		var node = e.target || e.srcElement;

		if (isLineNumCell(node)) {
			YAHOO.util.Event.stopEvent(e);

			var row = node.parentNode;

			gSelection.table = table;
			gSelection.lastSeenIndex = row.rowIndex;
			gSelection.begin    = gSelection.end    = node;
			gSelection.beginNum = gSelection.endNum = parseInt(node.innerHTML);
			getEl(row).addClass("selected");
		}
	});

	table.on('mouseup', function(e) {
		var node = e.target || e.srcElement;

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
				gotoAnchor(tbody.dom.getElementsByTagName("A")[0].name);
			}
		}
	});

	table.on('mouseover', function(e) {
		var node = getEl(e.target || e.srcElement);

		if (node.hasClass("commentflag")) {
			node = getEl(node.dom.parentNode);
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
						tag: 'img',
						src: '/images/comment-ghost.png'
					}, true);
					gGhostCommentFlag.enableDisplayMode();
					gGhostCommentFlag.setAbsolutePositioned();
					gGhostCommentFlag.setX(2);
				}

				gGhostCommentFlag.setTop(node.getY() - 1);
				gGhostCommentFlag.show();
			}
		}
	});

	table.on('mouseout', function(e) {
		var relTarget = e.relatedTarget || e.toElement;
		if (gGhostCommentFlag && relTarget != gGhostCommentFlag.dom) {
			gGhostCommentFlag.hide();
		}

		if (gSelection.table == table) {
			var fromNode = getEl(e.originalTarget);

			if (fromNode.hasClass("commentflag")) {
				fromNode = getEl(fromNode.dom.parentNode);
			}

			if (isLineNumCell(relTarget)) {
				var destRowIndex = relTarget.parentNode.rowIndex;

				if (destRowIndex >= gSelection.begin.parentNode.rowIndex) {
					for (var i = gSelection.lastSeenIndex;
						 i > relTarget.parentNode.rowIndex; i--) {
						getEl(table.dom.rows[i]).removeClass("selected");
					}
				}
			}
		}
	});

	for (linenum in lines) {
		linenum = parseInt(linenum);
		var cell = findLineNumCell(table.dom, linenum);

		if (cell != null) {
			new CommentBlock(fileid, cell, linenum, lines[linenum]);
		}
	}
}

function scrollToAnchor(anchor) {
	if (anchor == INVALID) {
		return false;
	}

	window.scrollTo(0,
		getEl(document.anchors[anchor]).getY() - DIFF_SCROLLDOWN_AMOUNT);
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
