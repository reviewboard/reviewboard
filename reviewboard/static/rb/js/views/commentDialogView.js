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
           '<a class="comment-list-view-action" href="<%= comment.url %>"><%- viewText %></a>',
           '<a class="comment-list-reply-action" href="<%= reviewRequestURL %>',
                    '?reply_id=<%= comment.reply_to_id || comment.comment_id %>',
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
            interactive = this.options.issuesInteractive,
            odd = true,
            $items = $();

        if (comments.length === 0) {
            return;
        }

        _.each(comments, function(serializedComment) {
            var commentID = serializedComment.comment_id,
                $item = $(this.itemTemplate({
                    comment: serializedComment,
                    itemClass: odd ? 'odd' : 'even',
                    reviewRequestURL: reviewRequestURL,
                    replyType: replyType,
                    viewText: gettext('View')
                })),
                commentIssueBar;

            if (serializedComment.issue_opened) {
                commentIssueBar = new RB.CommentIssueBarView({
                    reviewID: serializedComment.review_id,
                    commentID: commentID,
                    commentType: replyType,
                    issueStatus: serializedComment.issue_status,
                    interactive: interactive,
                    commentIssueManager: commentIssueManager
                });
                commentIssueBar.render().$el.appendTo($item);

                /*
                 * Update the serialized comment's issue status whenever
                 * the real comment's status is changed so we will
                 * display it correctly the next time we render it.
                 */
                commentIssueManager.on('issueStatusUpdated',
                                       function(comment) {
                    if (comment.id === commentID) {
                        serializedComment.issue_status =
                            comment.get('issueStatus');
                    }
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
    DIALOG_TOTAL_HEIGHT: 350,
    DIALOG_NON_EDITABLE_HEIGHT: 120,
    SLIDE_DISTANCE: 10,
    COMMENTS_BOX_WIDTH: 280,
    FORM_BOX_WIDTH: 450,

    className: 'comment-dlg',
    template: _.template([
        '<div class="other-comments">',
        ' <h1 class="title"><%- otherReviewsText %></h1>',
        ' <ul></ul>',
        '</div>',
        '<form method="post">',
        ' <h1 class="comment-dlg-header">',
        '  <span class="title"></span>',
        '<% if (authenticated && !hasDraft) { %>',
        '  <a class="markdown-info" href="<%- markdownDocsURL %>"',
        '     target="_blank"><%- markdownText %></a>',
        '<% } %>',
        ' </h1>',
        '<% if (!authenticated) { %>',
        ' <p class="login-text">',
        '  <%= loginText %>',
        ' </p>',
        '<% } else if (hasDraft) { %>',
        ' <p class="draft-warning"><%= draftWarning %></p>',
        '<% } %>',
        ' <div class="comment-dlg-body">',
        '  <div class="comment-text-field"></div>',
        '  <ul class="comment-dlg-options">',
        '   <li class="comment-issue-options">',
        '    <input type="checkbox" id="comment_issue" />',
        '    <label for="comment_issue" accesskey="i"><%= openAnIssueText %></label>',
        '   </li>',
        '   <li class="comment-markdown-options">',
        '    <input type="checkbox" id="enable_markdown" />',
        '    <label for="enable_markdown" accesskey="m"><%= enableMarkdownText %></label>',
        '   </li>',
        '  </ul>',
        ' </div>',
        ' <div class="comment-dlg-footer">',
        '  <div class="buttons">',
        '   <input type="button" class="save" value="<%- saveButton %>" ',
        '          disabled="true" />',
        '   <input type="button" class="cancel" value="<%- cancelButton %>" />',
        '   <input type="button" class="delete" value="<%- deleteButton %>" ',
        '          disabled="true" />',
        '   <input type="button" class="close" value="<%- closeButton %>" />',
        '  </div>',
        ' </div>',
        '</form>'
    ].join('')),

    events: {
        'click .buttons .cancel': '_onCancelClicked',
        'click .buttons .close': '_onCancelClicked',
        'click .buttons .delete': '_onDeleteClicked',
        'click .buttons .save': 'save',
        'keydown .comment-text-field': '_onTextKeyDown'
    },

    initialize: function() {
    },

    render: function() {
        var userSession = RB.UserSession.instance,
            reviewRequest = this.model.get('reviewRequest'),
            reviewRequestEditor = this.model.get('reviewRequestEditor');

        this.options.animate = (this.options.animate !== false);

        this.$el
            .hide()
            .html(this.template({
                authenticated: userSession.get('authenticated'),
                hasDraft: reviewRequest.get('hasDraft'),
                markdownDocsURL: MANUAL_URL + 'users/markdown/',
                markdownText: gettext('Markdown'),
                otherReviewsText: gettext('Other reviews'),
                loginText: interpolate(
                    gettext('You must <a href="%s">log in</a> to post a comment.'),
                    [userSession.get('loginURL')]),
                draftWarning: interpolate(
                    gettext('The review request\'s current <a href="%s">draft</a> needs to be published before you can comment.'),
                    [reviewRequest.get('reviewURL')]),
                openAnIssueText: gettext('Open an <u>I</u>ssue'),
                enableMarkdownText: gettext('Enable <u>M</u>arkdown'),
                saveButton: gettext('Save'),
                cancelButton: gettext('Cancel'),
                deleteButton: gettext('Delete'),
                closeButton: gettext('Close')
            }));

        this._$commentsPane = this.$('.other-comments');
        this._$draftForm = this.$('form');
        this._$body = this._$draftForm.children('.comment-dlg-body');
        this._$header = this._$draftForm.children('.comment-dlg-header');
        this._$footer = this._$draftForm.children('.comment-dlg-footer');
        this._$title = this._$header.children('.title');

        this._$commentOptions = this._$body.children('.comment-dlg-options');

        this._$issueOptions =
            this._$commentOptions.children(".comment-issue-options")
                .bindVisibility(this.model, 'canEdit');
        this._$markdownOptions =
            this._$commentOptions.children(".comment-markdown-options")
                .bindVisibility(this.model, 'canEdit');

        this._$issueField = this._$issueOptions.find('input')
            .bindProperty('checked', this.model, 'openIssue')
            .bindProperty('disabled', this.model, 'editing', {
                elementToModel: false,
                inverse: true
            });

        this._$enableMarkdownField = this._$markdownOptions.find('input')
            .bindProperty('checked', this.model, 'richText')
            .bindProperty('disabled', this.model, 'editing', {
                elementToModel: false,
                inverse: true
            });

        this.$buttons = this._$footer.find('.buttons');

        this.$saveButton = this.$buttons.find('input.save')
            .bindVisibility(this.model, 'canEdit')
            .bindProperty('disabled', this.model, 'canSave', {
                elementToModel: false,
                inverse: true
            });

        this.$cancelButton = this.$buttons.find('input.cancel')
            .bindVisibility(this.model, 'canEdit');

        this.$deleteButton = this.$buttons.find('input.delete')
            .bindVisibility(this.model, 'canDelete')
            .bindProperty('disabled', this.model, 'canDelete', {
                elementToModel: false,
                inverse: true
            });

        this.$closeButton = this.$buttons.find('input.close')
            .bindVisibility(this.model, 'canEdit', {
                inverse: true
            });

        this.commentsList = new CommentsListView({
            el: this._$commentsPane.find('ul'),
            reviewRequestURL: reviewRequest.get('reviewURL'),
            commentIssueManager: this.options.commentIssueManager,
            issuesInteractive: reviewRequestEditor.get('editable')
        });

        /*
         * We need to handle keypress here, rather than in events above,
         * because jQuery will actually handle it. Backbone fails to.
         */
        this._textEditor = new RB.TextEditorView({
            el: this._$draftForm.find('.comment-text-field'),
            autoSize: false,
            minHeight: 0,
            text: this.model.get('text'),
            bindRichText: {
                model: this.model,
                attrName: 'richText'
            }
        });
        this._textEditor.render();
        this._textEditor.show();
        this._textEditor.$el
            .keypress(_.bind(this._onTextKeyPress, this))
            .bindVisibility(this.model, 'canEdit');
        this._textEditor.on('change', function() {
            this.model.set('text', this._textEditor.getText());
        }, this);
        this._textEditor.bindRichTextCheckbox(this._$enableMarkdownField);
        this._textEditor.bindRichTextVisibility(
            this._$draftForm.find('.markdown-info'));

        this.listenTo(this.model, 'change:text', function() {
            this._textEditor.setText(this.model.get('text'));
        });

        this.listenTo(this.model, 'change:richText', this._handleResize);

        this.$el
            .css("position", "absolute")
            .mousedown(function(evt) {
                /*
                 * Prevent this from reaching the selection area, which will
                 * swallow the default action for the mouse down.
                 */
                evt.stopPropagation();
            })
            .resizable({
                handles: $.support.touch ? "grip,se"
                                         : "grip,n,e,s,w,se,sw,ne,nw",
                transparent: true,
                resize: _.bind(this._handleResize, this)
            })
            .proxyTouchEvents();

        this._$header.css('cursor', 'move');
        this.$el.draggable({
            handle: '.comment-dlg-header'
        });

        this.listenTo(this.model, 'change:dirty', this._updateTitle);
        this._updateTitle();

        this.model.on('change:publishedComments',
                      this._onPublishedCommentsChanged, this);
        this._onPublishedCommentsChanged();

        /* Add any hooks. */
        RB.CommentDialogHook.each(function(hook) {
            var HookViewType = hook.get('viewType'),
                hookView = new HookViewType({
                    commentDialog: this,
                    commentEditor: this.model,
                    el: this.el
                });

            hookView.render();
        }, this);

        return this;
    },

    /*
     * Callback for when the Save button is pressed.
     *
     * Saves the comment, creating it if it's new, and closes the dialog.
     */
    save: function() {
        /*
         * Set this immediately, in case new text has been set in the editor
         * that we haven't been notified about yet.
         */
        this.model.set('text', this._textEditor.getText());

        if (this.model.get('canSave')) {
            this.model.save({
                error: function(model, xhr) {
                    alert(gettext('Error saving comment: ') + xhr.errorText);
                }
            }, this);
            this.close();
        }
    },

    /*
     * Opens the comment dialog and focuses the text field.
     */
    open: function() {
        function openDialog() {
            this.$el.scrollIntoView();
            this._textEditor.focus();
        }

        this.$el
            .css({
                top: parseInt(this.$el.css("top"), 10) - this.SLIDE_DISTANCE,
                opacity: 0
            })
            .show();

        this._handleResize();

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
            }
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
     * Updates the title of the comment dialog, based on the current state.
     */
    _updateTitle: function() {
        this._$title.text(this.model.get('dirty')
                          ? gettext('Your comment (unsaved)')
                          : gettext('Your comment'));
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

        this.commentsList.setComments(comments,
                                       this.model.get('publishedCommentsType'));
        this._$commentsPane.setVisible(showComments);

        /* Do this here so that calculations can be done before open() */

        if (showComments) {
            width += this.COMMENTS_BOX_WIDTH;
        }

        this.$el
            .width(width)
            .height(this.model.get('canEdit')
                    ? this.DIALOG_TOTAL_HEIGHT
                    : this.DIALOG_NON_EDITABLE_HEIGHT);
    },

    /*
     * Handles the resize of the comment dialog. This will lay out the
     * elements in the dialog appropriately.
     */
    _handleResize: function() {
        var $draftForm = this._$draftForm,
            $commentsPane = this._$commentsPane,
            $commentsList = this.commentsList.$el,
            $textField = this._textEditor.$el,
            width = this.$el.width(),
            height = this.$el.height(),
            commentsWidth = 0;

        if ($commentsPane.is(":visible")) {
            $commentsPane
                .outerWidth(this.COMMENTS_BOX_WIDTH)
                .outerHeight(height)
                .move(0, 0, "absolute");

            $commentsList.height($commentsPane.height() -
                                 $commentsList.position().top);

            commentsWidth = $commentsPane.outerWidth(true);
            width -= commentsWidth;
        }

        $draftForm
            .outerWidth(width)
            .outerHeight(height)
            .move(commentsWidth, 0, "absolute");

        this._textEditor.setSize(
            (this._$body.width() -
             $textField.getExtents('b', 'lr')),
            ($draftForm.height() -
             this._$header.outerHeight() -
             this._$commentOptions.outerHeight() -
             this._$footer.outerHeight() -
             $textField.getExtents('b', 'tb')));
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
                    this.save();
                    return false;
                }
                break;

            case 73:
            case 105:
                /* I */
                if (e.altKey) {
                    this.model.set('openIssue', !this.model.get('openIssue'));
                }
                break;

            case 77:
            case 109:
                /* M */
                if (e.altKey) {
                    this.model.set('richText', !this.model.get('richText'));
                }
                break;

            default:
                break;
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
            reviewRequestEditor =
                options.reviewRequestEditor ||
                RB.PageManager.getPage().reviewRequestEditor,
            commentIssueManager =
                options.commentIssueManager ||
                reviewRequestEditor.get('commentIssueManager'),
            beside,
            dlg,
            x,
            y;

        function showCommentDlg() {
            try {
                dlg.open();
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
            commentIssueManager: commentIssueManager,
            model: new RB.CommentEditor({
                comment: options.comment,
                reviewRequest: reviewRequestEditor.get('reviewRequest'),
                reviewRequestEditor: reviewRequestEditor,
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
            beside = options.position.beside;
            dlg.positionBeside(beside.el, beside);
        } else {
            x = options.position.x;
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
