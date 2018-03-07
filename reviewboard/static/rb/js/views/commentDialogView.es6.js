(function() {


/**
 * Displays a list of existing comments within a comment dialog.
 *
 * Each comment in the list is an existing, published comment that a user
 * has made. They will be displayed, along with any issue states and
 * identifying information, and links for viewing the comment on the review
 * or replying to it.
 *
 * This is used internally in CommentDialogView.
 */
const CommentsListView = Backbone.View.extend({
    itemTemplate: _.template(dedent`
        <li class="<%= itemClass %>">
         <h2>
          <%- comment.user.name %>
          <span class="actions">
           <a class="comment-list-view-action" href="<%= comment.url %>"><%- viewText %></a>
           <a class="comment-list-reply-action"
              href="<%= reviewRequestURL %>?reply_id=<%= comment.reply_to_id || comment.comment_id %>&reply_type=<%= replyType %>"
              ><%- replyText %></a>
          </span>
         </h2>
         <pre><%- comment.text %></pre>
        </li>
    `),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     commentIssueManager (RB.CommentIssueManager):
     *         The manager for issues.
     *
     *     issuesInteractive (boolean):
     *         Whether the user can interact with issues (they have permission
     *         to change the state).
     *
     *     reviewRequestURL (string):
     *         The URL of the review request.
     */
    initialize(options) {
        this.options = options;
    },

    /**
     * Set the list of displayed comments.
     *
     * Args:
     *     comments (Array of object):
     *         The serialized comments.
     *
     *     replyType (string):
     *         The type of comment, for use in creating replies.
     */
    setComments(comments, replyType) {
        if (comments.length === 0) {
            return;
        }

        const reviewRequestURL = this.options.reviewRequestURL;
        const commentIssueManager = this.options.commentIssueManager;
        const interactive = this.options.issuesInteractive;
        let odd = true;
        let $items = $();

        _.each(comments, serializedComment => {
            const commentID = serializedComment.comment_id;
            const $item = $(this.itemTemplate({
                comment: serializedComment,
                itemClass: odd ? 'odd' : 'even',
                reviewRequestURL: reviewRequestURL,
                replyText: CommentsListView._replyText,
                replyType: replyType,
                viewText: CommentsListView._viewText,
            }));

            if (serializedComment.issue_opened) {
                const commentIssueBar = new RB.CommentIssueBarView({
                    reviewID: serializedComment.review_id,
                    commentID: commentID,
                    commentType: replyType,
                    issueStatus: serializedComment.issue_status,
                    interactive: interactive,
                    commentIssueManager: commentIssueManager,
                });
                commentIssueBar.render().$el.appendTo($item);

                /*
                 * Update the serialized comment's issue status whenever
                 * the real comment's status is changed so we will
                 * display it correctly the next time we render it.
                 */
                this.listenTo(
                    commentIssueManager, 'issueStatusUpdated', comment => {
                        if (comment.id === commentID) {
                            serializedComment.issue_status =
                                comment.get('issueStatus');
                        }
                    });
            }

            $items = $items.add($item);
            odd = !odd;
        });

        this.$el
            .empty()
            .append($items);
    },
},
{
    _replyText: gettext('Reply'),
    _viewText: gettext('View'),
});


/**
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
    DIALOG_READ_ONLY_HEIGHT: 104,
    SLIDE_DISTANCE: 10,
    COMMENTS_BOX_WIDTH: 280,
    FORM_BOX_WIDTH: 450,

    className: 'comment-dlg',
    template: _.template(dedent`
        <div class="other-comments">
         <h1 class="title"><%- otherReviewsText %></h1>
         <ul></ul>
        </div>
        <form method="post">
         <h1 class="comment-dlg-header">
          <span class="title"></span>
          <% if (authenticated && !hasDraft) { %>
           <a class="markdown-info" href="<%- markdownDocsURL %>"
              target="_blank"><%- markdownText %></a>
          <% } %>
         </h1>
         <% if (!authenticated) { %>
          <p class="login-text"><%= loginText %></p>
         <% } else if (readOnly) { %>
          <p class="read-only-text"><%= readOnlyText %></p>
         <% } else if (hasDraft) { %>
          <p class="draft-warning"><%= draftWarning %></p>
         <% } %>
         <div class="comment-dlg-body">
          <div class="comment-text-field"></div>
          <ul class="comment-dlg-options">
           <li class="comment-issue-options">
            <input type="checkbox" id="comment_issue">
            <label for="comment_issue" accesskey="i"><%= openAnIssueText %></label>
            <% if (showVerify) { %>
             <input type="checkbox" id="comment_issue_verify">
             <label for="comment_issue_verify"><%= verifyIssueText %></label>
            <% } %>
           </li>
           <li class="comment-markdown-options">
            <input type="checkbox" id="enable_markdown">
            <label for="enable_markdown" accesskey="m"><%= enableMarkdownText %></label>
           </li>
          </ul>
         </div>
         <div class="comment-dlg-footer">
          <div class="buttons">
           <input type="button" class="save" value="<%- saveButton %>"
                  disabled="true">
           <input type="button" class="cancel" value="<%- cancelButton %>">
           <input type="button" class="delete" value="<%- deleteButton %>"
                  disabled="true">
           <input type="button" class="close" value="<%- closeButton %>">
          </div>
         </div>
        </form>
    `),

    events: {
        'click .buttons .cancel': '_onCancelClicked',
        'click .buttons .close': '_onCancelClicked',
        'click .buttons .delete': '_onDeleteClicked',
        'click .buttons .save': 'save',
        'keydown .comment-text-field': '_onTextKeyDown',
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     animate (boolean):
     *         Whether to use animation.
     *
     *     commentIssueManager (RB.CommentIssueManager):
     *         The manager for issues.
     */
    initialize(options) {
        this.options = options;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.CommentDialogView:
     *     This object, for chaining.
     */
    render() {
        const userSession = RB.UserSession.instance;
        const reviewRequest = this.model.get('reviewRequest');
        const reviewRequestEditor = this.model.get('reviewRequestEditor');

        this.options.animate = (this.options.animate !== false);

        this.$el
            .hide()
            .html(this.template({
                authenticated: userSession.get('authenticated'),
                hasDraft: reviewRequest.get('hasDraft'),
                markdownDocsURL: MANUAL_URL + 'users/markdown/',
                markdownText: RB.CommentDialogView._markdownText,
                otherReviewsText: RB.CommentDialogView._otherReviewsText,
                loginText: interpolate(
                    RB.CommentDialogView._loginTextTemplate,
                    [userSession.get('loginURL')]),
                draftWarning: interpolate(
                    RB.CommentDialogView._draftWarningTextTemplate,
                    [reviewRequest.get('reviewURL')]),
                openAnIssueText: RB.CommentDialogView._openAnIssueText,
                enableMarkdownText: RB.CommentDialogView._enableMarkdownText,
                saveButton: RB.CommentDialogView._saveText,
                cancelButton: RB.CommentDialogView._cancelText,
                deleteButton: RB.CommentDialogView._deleteText,
                closeButton: RB.CommentDialogView._closeText,
                readOnly: userSession.get('readOnly'),
                readOnlyText: gettext('Review Board is currently in read-only mode.'),
                showVerify: RB.EnabledFeatures.issueVerification,
                verifyIssueText: RB.CommentDialogView._verifyIssueText,
            }));

        this._$commentsPane = this.$('.other-comments');
        this._$draftForm = this.$('form');
        this._$body = this._$draftForm.children('.comment-dlg-body');
        this._$header = this._$draftForm.children('.comment-dlg-header');
        this._$footer = this._$draftForm.children('.comment-dlg-footer');
        this._$title = this._$header.children('.title');

        this._$commentOptions = this._$body.children('.comment-dlg-options');

        this._$issueOptions =
            this._$commentOptions.children('.comment-issue-options')
                .bindVisibility(this.model, 'canEdit');
        this._$markdownOptions =
            this._$commentOptions.children('.comment-markdown-options')
                .bindVisibility(this.model, 'canEdit');

        this._$issueField = this._$issueOptions
            .find('#comment_issue')
                .bindProperty('checked', this.model, 'openIssue')
                .bindProperty('disabled', this.model, 'editing', {
                    elementToModel: false,
                    inverse: true,
                });

        this._$issueVerificationField = this._$issueOptions
            .find('#comment_issue_verify')
                .bindProperty('checked', this.model, 'requireVerification')
                .bindProperty('disabled', this.model, 'editing', {
                    elementToModel: false,
                    inverse: true,
                });

        this._$enableMarkdownField = this._$markdownOptions
            .find('#enable_markdown')
                .bindProperty('checked', this.model, 'richText')
                .bindProperty('disabled', this.model, 'editing', {
                    elementToModel: false,
                    inverse: true,
                });

        this.$buttons = this._$footer.find('.buttons');

        this.$saveButton = this.$buttons.find('input.save')
            .bindVisibility(this.model, 'canEdit')
            .bindProperty('disabled', this.model, 'canSave', {
                elementToModel: false,
                inverse: true,
            });

        this.$cancelButton = this.$buttons.find('input.cancel')
            .bindVisibility(this.model, 'canEdit');

        this.$deleteButton = this.$buttons.find('input.delete')
            .bindVisibility(this.model, 'canDelete')
            .bindProperty('disabled', this.model, 'canDelete', {
                elementToModel: false,
                inverse: true,
            });

        this.$closeButton = this.$buttons.find('input.close')
            .bindVisibility(this.model, 'canEdit', {
                inverse: true,
            });

        this.commentsList = new CommentsListView({
            el: this._$commentsPane.find('ul'),
            reviewRequestURL: reviewRequest.get('reviewURL'),
            commentIssueManager: this.options.commentIssueManager,
            issuesInteractive: reviewRequestEditor.get('editable'),
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
                attrName: 'richText',
            },
        });
        this._textEditor.render();
        this._textEditor.show();
        this._textEditor.$el.bindVisibility(this.model, 'canEdit');
        this.listenTo(this._textEditor, 'change',
                      () => this.model.set('text',
                                           this._textEditor.getText()));
        this._textEditor.bindRichTextCheckbox(this._$enableMarkdownField);
        this._textEditor.bindRichTextVisibility(
            this._$draftForm.find('.markdown-info'));

        this.listenTo(this.model, 'change:text',
                      () => this._textEditor.setText(this.model.get('text')));

        this.listenTo(this.model, 'change:richText', this._handleResize);

        this.$el
            .css('position', 'absolute')
            .mousedown(evt => {
                /*
                 * Prevent this from reaching the selection area, which will
                 * swallow the default action for the mouse down.
                 */
                evt.stopPropagation();
            })
            .resizable({
                handles: $.support.touch ? 'grip,se'
                                         : 'grip,n,e,s,w,se,sw,ne,nw',
                transparent: true,
                resize: _.bind(this._handleResize, this),
            })
            .proxyTouchEvents();

        this._$header.css('cursor', 'move');
        this.$el.draggable({
            handle: '.comment-dlg-header',
        });

        this.listenTo(this.model, 'change:dirty', this._updateTitle);
        this._updateTitle();

        this.listenTo(this.model, 'change:publishedComments',
                      () => this._onPublishedCommentsChanged());
        this._onPublishedCommentsChanged();

        /* Add any hooks. */
        RB.CommentDialogHook.each(hook => {
            const HookViewType = hook.get('viewType');
            const hookView = new HookViewType({
                extension: hook.get('extension'),
                commentDialog: this,
                commentEditor: this.model,
                el: this.el,
            });

            hookView.render();
        });

        return this;
    },

    /**
     * Callback for when the Save button is pressed.
     *
     * Saves the comment, creating it if it's new, and closes the dialog.
     */
    save() {
        /*
         * Set this immediately, in case new text has been set in the editor
         * that we haven't been notified about yet.
         */
        this.model.set('text', this._textEditor.getText());

        if (this.model.get('canSave')) {
            this.model.save({
                error: (model, xhr) => {
                    alert(gettext('Error saving comment: ') + xhr.errorText);
                }
            });
            this.close();
        }
    },

    /**
     * Open the comment dialog and focuses the text field.
     */
    open() {
        function openDialog() {
            this.$el.scrollIntoView();
            this._textEditor.focus();
        }

        this.$el
            .css({
                top: parseInt(this.$el.css('top'), 10) - this.SLIDE_DISTANCE,
                opacity: 0,
            })
            .show();

        this._handleResize();

        if (this.model.get('canEdit')) {
            this.model.beginEdit();
        }

        if (this.options.animate) {
            this.$el.animate({
                top: `+=${this.SLIDE_DISTANCE}px`,
                opacity: 1,
            }, 350, 'swing', _.bind(openDialog, this));
        } else {
            openDialog.call(this);
        }
    },

    /**
     * Close the comment dialog, discarding the comment block if empty.
     *
     * This can optionally take a callback and context to notify when the
     * dialog has been closed.
     *
     * Args:
     *     onClosed (function, optional):
     *         An optional callback to call once the dialog has been closed.
     *
     *     context (object, optional):
     *         Context to use when calling ``onClosed``.
     */
    close(onClosed=undefined, context={}) {
        function closeDialog() {
            this.model.close();
            this.$el.remove();
            this.trigger('closed');

            if (_.isFunction(onClosed)) {
                onClosed.call(context);
            }
        }

        if (this.options.animate && this.$el.is(':visible')) {
            this.$el.animate({
                top: `-=${this.SLIDE_DISTANCE}px`,
                opacity: 0,
            }, 350, 'swing', _.bind(closeDialog, this));
        } else {
            closeDialog.call(this);
        }
    },

    /**
     * Move the comment dialog to the given coordinates.
     *
     * Args:
     *     x (number):
     *         The X-coordinate to move the dialog to.
     *
     *     y (number):
     *         The Y-coordinate to move the dialog to.
     */
    move(x, y) {
        this.$el.move(x, y);
    },

    /**
     * Position the dialog beside an element.
     *
     * This takes the same arguments that $.fn.positionToSide takes.
     *
     * Args:
     *     $el (jQuery):
     *        The element to move the dialog next to.
     *
     *     options (object):
     *         Options for the ``positionToSide`` call.
     */
    positionBeside($el, options) {
        this.$el.positionToSide($el, options);
    },

    /**
     * Update the title of the comment dialog, based on the current state.
     */
    _updateTitle() {
        this._$title.text(this.model.get('dirty')
                          ? RB.CommentDialogView._yourCommentDirtyText
                          : RB.CommentDialogView._yourCommentText);
    },

    /**
     * Callback for when the list of published comments changes.
     *
     * Sets the list of comments in the CommentsList, and factors in some
     * new layout properties.
     */
    _onPublishedCommentsChanged() {
        const comments = this.model.get('publishedComments') || [];
        this.commentsList.setComments(comments,
                                       this.model.get('publishedCommentsType'));

        const showComments = (comments.length > 0);
        this._$commentsPane.setVisible(showComments);

        /* Do this here so that calculations can be done before open() */
        let width = this.FORM_BOX_WIDTH;

        if (showComments) {
            width += this.COMMENTS_BOX_WIDTH;
        }

        let height;

        if (this.model.get('canEdit')) {
            height = this.DIALOG_TOTAL_HEIGHT;
        } else if (RB.UserSession.instance.get('readOnly')) {
            height = this.DIALOG_READ_ONLY_HEIGHT;
        } else {
            height = this.DIALOG_NON_EDITABLE_HEIGHT;
        }

        this.$el
            .width(width)
            .height(height);
    },

    /**
     * Handle the resize of the comment dialog.
     *
     * This will lay out the elements in the dialog appropriately.
     */
    _handleResize() {
        const height = this.$el.height();
        let width = this.$el.width();
        let commentsWidth = 0;

        if (this._$commentsPane.is(':visible')) {
            this._$commentsPane
                .outerWidth(this.COMMENTS_BOX_WIDTH)
                .outerHeight(height)
                .move(0, 0, 'absolute');

            const $commentsList = this.commentsList.$el;
            $commentsList.height(this._$commentsPane.height() -
                                 $commentsList.position().top);

            commentsWidth = this._$commentsPane.outerWidth(true);
            width -= commentsWidth;
        }

        this._$draftForm
            .outerWidth(width)
            .outerHeight(height)
            .move(commentsWidth, 0, 'absolute');

        const $textField = this._textEditor.$el;
        this._textEditor.setSize(
            (this._$body.width() -
             $textField.getExtents('b', 'lr')),
            (this._$draftForm.height() -
             this._$header.outerHeight() -
             this._$commentOptions.outerHeight() -
             this._$footer.outerHeight() -
             $textField.getExtents('b', 'tb')));
    },

    /**
     * Callback for when the Cancel button is pressed.
     *
     * Cancels the comment (which may delete the comment block, if it's new)
     * and closes the dialog.
     */
    _onCancelClicked() {
        let shouldExit = true;

        if (this.model.get('dirty')) {
            shouldExit = confirm(RB.CommentDialogView._shouldExitText);
        }

        if (shouldExit) {
            this.model.cancel();
            this.close();
        }
    },

    /**
     * Callback for when the Delete button is pressed.
     *
     * Deletes the comment and closes the dialog.
     */
    _onDeleteClicked() {
        if (this.model.get('canDelete')) {
            this.model.deleteComment();
            this.close();
        }
    },

    /**
     * Callback for keydown events in the text field.
     *
     * If the Escape key is pressed, the dialog will be closed.
     * If the Control-Enter or Alt-I keys are pressed, we'll handle them
     * specially. Control-Enter is the same thing as clicking Save.
     *
     * metaKey used as alternative for Mac key shortcut philosophy.
     * metaKey is only fired on keydown in Chrome and Brave.
     *
     * The keydown event won't be propagated to the parent elements.
     *
     * Args:
     *     e (Event):
     *         The keydown event.
     */
    _onTextKeyDown(e) {
        e.stopPropagation();

        switch (e.which) {
            case $.ui.keyCode.ESCAPE:
                this._onCancelClicked();
                return false;

            case 10:
            case $.ui.keyCode.ENTER:
                /* Enter */
                if (e.metaKey || e.ctrlKey) {
                    this.save();
                    e.preventDefault();
                    e.stopPropagation();
                }
                break;

            case 73:
            case 105:
                /* I */
                if (e.metaKey || e.altKey) {
                    // preventDefault is called to avoid Firefox info window.
                    e.preventDefault();
                    this.model.set('openIssue', !this.model.get('openIssue'));
                }
                break;

            case 77:
            case 109:
                /* M */
                if (e.metaKey || e.altKey) {
                    // preventDefault is called to avoid Mac's window minimize.
                    e.preventDefault();
                    this.model.set('richText', !this.model.get('richText'));
                }
                break;

            default:
                break;
        }
    },
}, {
    /**
     * The singleton instance.
     */
    _instance: null,

    /**
     * Create and shows a new comment dialog and associated model.
     *
     * This is a class method that handles providing a comment dialog
     * ready to use with the given state.
     *
     * Only one comment dialog can appear on the screen at any given time
     * when using this.
     *
     * Args:
     *     options (object, optional):
     *         Options for the view construction.
     */
    create: function(options={}) {
        console.assert(options.comment, 'A comment must be specified');

        const reviewRequestEditor =
            options.reviewRequestEditor ||
            RB.PageManager.getPage().model.reviewRequestEditor;

        const dlg = new RB.CommentDialogView({
            animate: options.animate,
            commentIssueManager: options.commentIssueManager ||
                                 reviewRequestEditor.get('commentIssueManager'),
            model: new RB.CommentEditor({
                comment: options.comment,
                reviewRequest: reviewRequestEditor.get('reviewRequest'),
                reviewRequestEditor: reviewRequestEditor,
                publishedComments: options.publishedComments || undefined,
                publishedCommentsType: options.publishedCommentsType ||
                                       undefined,
            })
        });

        dlg.render().$el
            .css('z-index', 999) // XXX Use classes for z-indexes.
            .appendTo(options.container || document.body);

        options.position = options.position || {};

        if (_.isFunction(options.position)) {
            options.position(dlg);
        } else if (options.position.beside) {
            dlg.positionBeside(options.position.beside.el,
                               options.position.beside);
        } else {
            let x = options.position.x;
            let y = options.position.y;

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

        dlg.on('closed', () => RB.CommentDialogView._instance = null);

        const instance = RB.CommentDialogView._instance;
        const showCommentDlg = function showCommentDlg() {
            try {
                dlg.open();
            } catch(e) {
                dlg.close();
                throw e;
            }

            RB.CommentDialogView._instance = dlg;
        };

        if (instance) {
            instance.on('closed', showCommentDlg);
            instance.close();
        } else {
            showCommentDlg();
        }

        return dlg;
    },

    _cancelText: gettext('Cancel'),
    _closeText: gettext('Close'),
    _deleteText: gettext('Delete'),
    _draftWarningTextTemplate: gettext('The review request\'s current <a href="%s">draft</a> needs to be published before you can comment.'),
    _enableMarkdownText: gettext('Enable <u>M</u>arkdown'),
    _loginTextTemplate: gettext('You must <a href="%s">log in</a> to post a comment.'),
    _markdownText: gettext('Markdown'),
    _openAnIssueText: gettext('Open an <u>I</u>ssue'),
    _otherReviewsText: gettext('Other reviews'),
    _saveText: gettext('Save'),
    _shouldExitText: gettext('You have unsaved changes. Are you sure you want to exit?'),
    _verifyIssueText: gettext('Require Verification'),
    _yourCommentText: gettext('Your comment'),
    _yourCommentDirtyText: gettext('Your comment (unsaved)'),
});


})();
