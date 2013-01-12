/*
 * Displays a list of existing comments within a comment dialog.
 *
 * Each comment in the list is an existing, published comment that a user
 * has made. They will be displayed, along with any issue states and
 * identifying information, and links for viewing the comment on the review
 * or replying to it.
 *
 * This is used internally in CommentDialogView.
 */
var CommentsListView = Backbone.View.extend({
    itemTemplate: _.template([
        '<li class="<%= itemClass %>">',
         '<h2>',
          '<%- comment.user.name %>',
          '<span class="actions">',
           '<a href="<%= comment.url %>">View</a>',
           '<a href="<%= reviewRequestURL %>',
                    '?reply_id=<%= comment.comment_id %>',
                    '&reply_type=<%= replyType %>">Reply</a>',
          '</span>',
         '</h2>',
         '<pre><%- comment.text %></pre>'
    ].join('')),

    /*
     * Set the list of displayed comments.
     */
    setComments: function(comments, replyType) {
        var reviewRequestURL = this.options.reviewRequestURL,
            commentIssueManager = this.options.commentIssueManager,
            odd = true,
            $items = $();

        if (comments.length === 0) {
            return;
        }

        _.each(comments, function(comment) {
            var $item = $(this.itemTemplate({
                comment: comment,
                itemClass: odd ? 'odd' : 'even',
                reviewRequestURL: reviewRequestURL,
                replyType: replyType
            }));

            if (comment.issue_opened) {
                var interactive = window['gEditable'],
                    $issue = $('<div/>').issueIndicator();

                if (interactive) {
                    $issue.issueButtons();
                }

                $issue
                    .commentIssue(comment.review_id, comment.comment_id,
                                  replyType, comment.issue_status,
                                  interactive)
                    .appendTo($item);

                commentIssueManager.registerCallback(comment.comment_id,
                    function(issue_status) {
                        comment.issue_status = issue_status;
                    });
            }

            $items = $items.add($item);

            odd = !odd;
        }, this);

        this.$el
            .empty()
            .append($items);
    }
});


/*
 * A dialog that allows for creating, editing or deleting draft comments on
 * a diff or file attachment. The dialog can be moved around on the page.
 *
 * Any existing comments for the selected region will be displayed alongside
 * the dialog for reference. However, this dialog is not intended to be
 * used to reply to those comments.
 */
RB.CommentDialogView = Backbone.View.extend({
    DIALOG_TOTAL_HEIGHT: 250,
    SLIDE_DISTANCE: 10,
    COMMENTS_BOX_WIDTH: 280,
    FORM_BOX_WIDTH: 380,

    className: 'comment-dlg',
    template: _.template($('#comment-dlg-template').html()),

    events: {
        'click .buttons .cancel': '_onCancelClicked',
        'click .buttons .delete': '_onDeleteClicked',
        'click .buttons .save': '_onSaveClicked',
        'keydown textarea': '_onTextKeyDown',
        'keyup textarea': '_onTextKeyUp'
    },

    initialize: function() {
        this._ignoreKeyUp = false;
    },

    render: function() {
        this.options.animate = (this.options.animate !== false);

        this.$el
            .hide()
            .html(this.template());

        this._$draftForm    = this.$el.find('form');
        this._$commentsPane = this.$el.find('.other-comments');
        this._$buttons      = this._$draftForm.find(".buttons");
        this._$statusField  = this._$draftForm.find(".status");
        this._$issueOptions = this._$draftForm.find(".comment-issue-options");

        this._$issueField = this._$issueOptions.find('input')
            .bindProperty('checked', this.model, 'openIssue')
            .bindProperty('disabled', this.model, 'editing', {
                elementToModel: false,
                inverse: true
            });

        this._$saveButton = this._$buttons.find('input.save')
            .bindProperty('disabled', this.model, 'canSave', {
                elementToModel: false,
                inverse: true
            });

        this._$cancelButton = this._$buttons.find('input.cancel');

        this._$deleteButton = this._$buttons.find('input.delete')
            .bindVisibility(this.model, 'canDelete')
            .bindProperty('disabled', this.model, 'canDelete', {
                elementToModel: false,
                inverse: true
            });

        this._commentsList = new CommentsListView({
            el: this._$commentsPane.find('ul'),
            reviewRequestURL: this.options.reviewRequestURL,
            commentIssueManager: this.options.commentIssueManager
        });

        /*
         * We need to handle keypress here, rather than in events above,
         * because jQuery will actually handle it. Backbone fails to.
         */
        this._$textField = this._$draftForm.find('textarea')
            .keypress(_.bind(this._onTextKeyPress, this))
            .bindProperty('disabled', this.model, 'canEdit', {
                elementToModel: false,
                inverse: true
            })
            .bindProperty('value', this.model, 'text', {
                elementToModel: false
            });

        this.$el
            .css("position", "absolute")
            .mousedown(function(evt) {
                /*
                 * Prevent this from reaching the selection area, which will
                 * swallow the default action for the mouse down.
                 */
                evt.stopPropagation();
            })
            .proxyTouchEvents();

        if (!$.browser.msie || $.browser.version >= 9) {
            /*
             * resizable is pretty broken in IE 6/7.
             */
            var grip = $("<img/>")
                .addClass("ui-resizable-handle ui-resizable-grip")
                .attr("src", STATIC_URLS["rb/images/resize-grip.png"])
                .insertAfter(this._$buttons)
                .proxyTouchEvents();

            this.$el.resizable({
                handles: $.browser.mobileSafari ? "grip,se"
                                                : "grip,n,e,s,w,se,sw,ne,nw",
                transparent: true,
                resize: _.bind(this._handleResize, this)
            });

            /* Reset the opacity, which resizable() changes. */
            grip.css("opacity", 100);
        }

        if (!$.browser.msie || $.browser.version >= 7) {
            /*
             * draggable works in IE7 and up, but not IE6.
             */
            this.$el.draggable({
                handle: $(".title", this).css("cursor", "move")
            });
        }

        this.model.on('change:dirty', function() {
            if (this.$el.is(':visible')) {
                this._handleResize();
            }
        }, this);

        this.model.on('change:statusText', function(model, text) {
            this._$statusField.text(text || '');
        }, this);

        this.model.on('change:publishedComments',
                      this._onPublishedCommentsChanged, this);
        this._onPublishedCommentsChanged();

        return this;
    },

    /*
     * Opens the comment dialog and focuses the text field.
     */
    open: function(fromEl) {
        function openDialog() {
            this.$el.scrollIntoView();
            this._$textField.focus();
        }

        this.$el
            .css({
                top: parseInt(this.$el.css("top"), 10) - this.SLIDE_DISTANCE,
                opacity: 0
            })
            .show();

        this._handleResize()

        if (this.model.get('canEdit')) {
            this.model.beginEdit();
        }

        if (this.options.animate) {
            this.$el.animate({
                top: "+=" + this.SLIDE_DISTANCE + "px",
                opacity: 1
            }, 350, "swing", _.bind(openDialog, this));
        } else {
            openDialog.call(this);
        }
    },

    /*
     * Closes the comment dialog, discarding the comment block if empty.
     *
     * This can optionally take a callback and context to notify when the
     * dialog has been closed.
     */
    close: function(onClosed, context) {
        function closeDialog() {
            this.model.close();
            this.$el.remove();
            this.trigger("closed");

            if (_.isFunction(onClosed)) {
                onClosed.call(context);
            };
        }

        if (this.options.animate && this.$el.is(":visible")) {
            this.$el.animate({
                top: "-=" + this.SLIDE_DISTANCE + "px",
                opacity: 0
            }, 350, "swing", _.bind(closeDialog, this));
        } else {
            closeDialog.call(this);
        }
    },

    /*
     * Moves the comment dialog to the given coordinates.
     */
    move: function(x, y) {
        this.$el.move(x, y);
    },

    /*
     * Positions the dialog beside an element.
     *
     * This takes the same arguments that $.fn.positionToSide takes.
     */
    positionBeside: function($el, options) {
        this.$el.positionToSide($el, options);
    },

    /*
     * Callback for when the list of published comments changes.
     *
     * Sets the list of comments in the CommentsList, and factors in some
     * new layout properties.
     */
    _onPublishedCommentsChanged: function() {
        var comments = this.model.get('publishedComments') || [],
            showComments = (comments.length > 0),
            width = this.FORM_BOX_WIDTH;

        this._commentsList.setComments(comments,
                                       this.model.get('publishedCommentsType'));
        this._$commentsPane.setVisible(showComments);

        /* Do this here so that calculations can be done before open() */

        if (showComments) {
            width += this.COMMENTS_BOX_WIDTH;
        }

        /* Don't let the text field bump up the size we set below. */
        this._$textField
            .width(10)
            .height(10);

        this.$el
            .width(width)
            .height(this.DIALOG_TOTAL_HEIGHT);
    },

    /*
     * Handles the resize of the comment dialog. This will lay out the
     * elements in the dialog appropriately.
     */
    _handleResize: function() {
        var $draftForm = this._$draftForm,
            $commentsPane = this._$commentsPane,
            $commentsList = this._commentsList.$el,
            $textField = this._$textField,
            textFieldPos,
            width = this.$el.width(),
            height = this.$el.height(),
            formWidth = width - $draftForm.getExtents("bp", "lr"),
            boxHeight = height,
            commentsWidth = 0;

        if ($commentsPane.is(":visible")) {
            $commentsPane
                .width(this.COMMENTS_BOX_WIDTH -
                       $commentsPane.getExtents("bp", "lr"))
                .height(boxHeight - $commentsPane.getExtents("bp", "tb"))
                .move(0, 0, "absolute");

            $commentsList.height($commentsPane.height() -
                                 $commentsList.position().top -
                                 $commentsList.getExtents("bmp", "b"));

            commentsWidth = $commentsPane.outerWidth(true);
            formWidth -= commentsWidth;
        }

        $draftForm
            .width(formWidth)
            .height(boxHeight - $draftForm.getExtents("bp", "tb"))
            .move(commentsWidth, 0, "absolute");

        textFieldPos = $textField.position();

        $textField
            .width($draftForm.width() - textFieldPos.left -
                   $textField.getExtents("bmp", "r"))
            .height($draftForm.height() - textFieldPos.top -
                    this._$buttons.outerHeight(true) -
                    this._$statusField.height() -
                    this._$issueOptions.height() -
                    $textField.getExtents("bmp", "b"));
    },

    /*
     * Callback for when the Cancel button is pressed.
     *
     * Cancels the comment (which may delete the comment block, if it's new)
     * and closes the dialog.
     */
    _onCancelClicked: function() {
        this.model.cancel();
        this.close();
    },

    /*
     * Callback for when the Delete button is pressed.
     *
     * Deletes the comment and closes the dialog.
     */
    _onDeleteClicked: function() {
        if (this.model.get('canDelete')) {
            this.model.deleteComment();
            this.close();
        }
    },

    /*
     * Callback for when the Save button is pressed.
     *
     * Saves the comment, creating it if it's new, and closes the dialog.
     */
    _onSaveClicked: function() {
        if (this.model.get('canSave')) {
            this.model.save({
                error: function(model, errMsg) {
                    alert('Error saving comment: ' + errMsg);
                }
            }, this);
            this.close();
        }
    },

    /*
     * Callback for key down events in the text field.
     *
     * If the Escape key is pressed, the dialog will be closed.
     *
     * The keydown event won't be propagated to the parent elements.
     */
    _onTextKeyDown: function(e) {
        e.stopPropagation();

        if (e.which === $.ui.keyCode.ESCAPE) {
            this._onCancelClicked();
            return false;
        }
    },

    /*
     * Callback for key press events in the text field.
     *
     * If the Control-Enter or Alt-I keys are pressed, we'll handle them
     * specially. Control-enter is the same thing as clicking Save,
     * and Alt-I is the same as toggling the Issue checkbox.
     */
    _onTextKeyPress: function(e) {
        e.stopPropagation();

        switch (e.which) {
            case 10:
            case $.ui.keyCode.ENTER:
                /* Enter */
                if (e.ctrlKey) {
                    this._ignoreKeyUp = true;
                    this._onSaveClicked();
                    return false;
                }
                break;

            case 73:
            case 105:
                /* I */
                if (e.altKey) {
                    this.model.set('openIssue', !this.model.get('openIssue'));
                    this._ignoreKeyUp = true;
                }
                break;

            default:
                this._ignoreKeyUp = false;
                break;
        }
    },

    /*
     * Callback for key up events in the text field.
     *
     * If the key isn't being ignored due to a special key combination
     * (Control-S, Alt-I), then we update the model with the new text.
     */
    _onTextKeyUp: function(e) {
        /*
         * We check if we want to ignore this event. The state from
         * some shortcuts (control-enter) may not be settled, and we
         * may end up setting this to dirty, causing page leave
         * confirmations.
         */
        if (!this._ignoreKeyUp) {
            e.stopPropagation();

            this.model.set('text', this._$textField.val());
        }
    }
}, {
    /*
     * Add some useful singletons to CommentDialogView for managing
     * comment dialogs.
     */

    _instance: null,

    /*
     * Creates and shows a new comment dialog and associated model.
     *
     * This is a class method that handles providing a comment dialog
     * ready to use with the given state.
     *
     * Only one comment dialog can appear on the screen at any given time
     * when using this.
     */
    create: function(options) {
        var instance = RB.CommentDialogView._instance,
            dlg;

        function showCommentDlg() {
            try {
                dlg.open(options.fromEl);
            } catch(e) {
                dlg.close();
                throw e;
            }

            RB.CommentDialogView._instance = dlg;
        }

        console.assert(options.comment, 'A comment must be specified');

        options = options || {};

        dlg = new RB.CommentDialogView({
            animate: options.animate,
            commentIssueManager: gCommentIssueManager,
            reviewRequestURL: options.reviewRequestURL,
            model: new RB.CommentEditor({
                comment: options.comment,
                publishedComments: options.publishedComments || undefined,
                publishedCommentsType: options.publishedCommentsType ||
                                       undefined
            })
        });

        dlg.render().$el
            .css('z-index', 999) // XXX Use classes for z-indexes.
            .appendTo(options.container || document.body);

        options.position = options.position || {};

        if (_.isFunction(options.position)) {
            options.position(dlg);
        } else if (options.position.beside) {
            var beside = options.position.beside;
            dlg.positionBeside(beside.el, beside);
        } else {
            var x = options.position.x,
                y = options.position.y;

            if (x === undefined) {
                /* Center it. */
                x = $(document).scrollLeft() +
                    ($(window).width() - dlg.$el.width()) / 2;
            }

            if (y === undefined) {
                /* Center it. */
                y = $(document).scrollTop() +
                    ($(window).height() - dlg.$el.height()) / 2;
            }

            dlg.move(x, y);
        }

        dlg.on('closed', function() {
            RB.CommentDialogView._instance = null;
        });

        if (instance) {
            instance.on('closed', showCommentDlg);
            instance.close();
        } else {
            showCommentDlg();
        }

        return dlg;
    }
});
