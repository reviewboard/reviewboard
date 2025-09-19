/**
 * The comment dialog.
 */
import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';

import {
    type BaseComment,
    EnabledFeatures,
    UserSession,
} from 'reviewboard/common';
import { CommentDialogHook } from 'reviewboard/extensions';
import { TextEditorView } from 'reviewboard/ui';

import { type SerializedComment } from '../models/commentData';
import { CommentEditor } from '../models/commentEditorModel';
import { type ReviewRequestEditor } from '../models/reviewRequestEditorModel';


/**
 * Options for the CommentsListView.
 *
 * Version Added:
 *     6.0
 */
interface CommentsListViewOptions {
    /** The issue manager. */
    commentIssueManager: RB.CommentIssueManager;

    /** Whether the user can change issue states. */
    issuesInteractive: boolean;

    /** The URL of the review request. */
    reviewRequestURL: string;
}


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
@spina
class CommentsListView extends BaseView<
    undefined,
    HTMLDivElement,
    CommentsListViewOptions
> {
    static itemTemplate = _.template(dedent`
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
    `);

    static replyText = _`Reply`;
    static viewText = _`View`;

    /**********************
     * Instance variables *
     **********************/

    /** Options for the view. */
    options: CommentsListViewOptions;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (CommentsListViewOptions):
     *         Options for the view.
     */
    initialize(options: CommentsListViewOptions) {
        this.options = options;
    }

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
    setComments(
        comments: SerializedComment[],
        replyType: string,
    ) {
        if (comments.length === 0) {
            return;
        }

        const reviewRequestURL = this.options.reviewRequestURL;
        const commentIssueManager = this.options.commentIssueManager;
        const interactive = this.options.issuesInteractive;
        let odd = true;
        let $items = $();

        comments.forEach(serializedComment => {
            const commentID = serializedComment.comment_id;
            const $item = $(CommentsListView.itemTemplate({
                comment: serializedComment,
                itemClass: odd ? 'odd' : 'even',
                replyText: CommentsListView.replyText,
                replyType: replyType,
                reviewRequestURL: reviewRequestURL,
                viewText: CommentsListView.viewText,
            }));

            if (serializedComment.issue_opened) {
                const commentIssueBar = new RB.CommentIssueBarView({
                    commentID: commentID,
                    commentIssueManager: commentIssueManager,
                    commentType: replyType,
                    interactive: interactive,
                    isCompact: true,
                    issueStatus: serializedComment.issue_status,
                    reviewID: serializedComment.review_id,
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
    }
}


/**
 * Options for the CommentDialogView.
 */
interface CommentDialogViewOptions {
    /** Whether to use animation. */
    animate?: boolean;

    /** The issue manager. */
    commentIssueManager?: RB.CommentIssueManager;

    /**
     * The warning to show to the user about deleted objects.
     *
     * If the user is trying to comment on a deleted object (such as a file
     * attachment that has been deleted), show this warning to them and
     * block them from commenting.
     *
     * Version Added:
     *     6.0
     */
    deletedWarning: string;

    /**
     * The warning to show to the user about draft objects.
     *
     * If the user is commenting on a draft object (such as a diff or file
     * attachment that has not yet been published), show this warning to them.
     */
    draftWarning: string;
}


/**
 * Options for creating the CommentDialogView.
 */
interface CommentDialogViewCreationOptions {
    /** Whether to use animation. */
    animate?: boolean;

    /** The comment text. */
    comment: BaseComment;

    /** The issue manager. */
    commentIssueManager?: RB.CommentIssueManager;

    /** The container to add the dialog to. */
    container: HTMLElement | JQuery;

    /**
     * The warning to show to the user about deleted objects.
     *
     * If the user is trying to comment on a deleted object (such as a file
     * attachment that has been deleted), show this warning to them and
     * block them from commenting.
     *
     * Version Added:
     *     6.0
     */
    deletedWarning?: string;

    /**
     * The warning to show to the user about draft objects.
     *
     * If the user is commenting on a draft object (such as a diff or file
     * attachment that has not yet been published), show this warning to them.
     */
    draftWarning?: string;

    /** Position information for the dialog. */
    position?: any;

    /**
     * The thread of previous comments that this draft is a reply to.
     *
     * This only applies if the comment is a reply.
     */
    publishedComments?: SerializedComment[];

    /**
     * The type of comment that this draft is a reply to.
     *
     * This only applies if the comment is a reply.
     */
    publishedCommentsType?: string;

    /** The review request editor. */
    reviewRequestEditor?: ReviewRequestEditor;
}


/**
 * A dialog that allows for creating, editing or deleting draft comments on
 * a diff or file attachment. The dialog can be moved around on the page.
 *
 * Any existing comments for the selected region will be displayed alongside
 * the dialog for reference. However, this dialog is not intended to be
 * used to reply to those comments.
 */
@spina
export class CommentDialogView extends BaseView<
    CommentEditor,
    HTMLDivElement,
    CommentDialogViewOptions
> {
    static className = 'comment-dlg';

    static events: EventsHash = {
        'click .btn-cancel': '_onCancelClicked',
        'click .btn-close': '_onCancelClicked',
        'click .btn-delete': '_onDeleteClicked',
        'click .btn-save': 'save',
        'keydown .comment-text-field': '_onTextKeyDown',
        'scroll': '_onScroll',
        'wheel': '_onScroll',
    };

    /** The singleton instance. */
    static _instance = null;

    static DIALOG_TOTAL_HEIGHT = 350;
    static DIALOG_TOTAL_HEIGHT_PORTRAIT = 400;
    static DIALOG_NON_EDITABLE_HEIGHT = 120;
    static DIALOG_READ_ONLY_HEIGHT = 104;
    static SLIDE_DISTANCE = 10;
    static COMMENTS_BOX_WIDTH = 280;
    static COMMENTS_BOX_HEIGHT_PORTRAIT = 175;
    static FORM_BOX_WIDTH = 450;

    static _cancelText = _`Cancel`;
    static _closeText = _`Close`;
    static _deleteText = _`Delete`;
    static _enableMarkdownText = _`Enable <u>M</u>arkdown`;
    static _loginTextTemplate = _`You must <a href="%s">log in</a> to post a comment.`;
    static _markdownText = _`Markdown`;
    static _openAnIssueText = _`Open an <u>I</u>ssue`;
    static _otherReviewsText = _`Other reviews`;
    static _saveText = _`Save`;
    static _shouldExitText = _`You have unsaved changes. Are you sure you want to exit?`;
    static _verifyIssueText = _`Require Verification`;
    static _yourCommentText = _`Your comment`;
    static _yourCommentDirtyText = _`Your comment (unsaved)`;

    static template = _.template(dedent`
        <div class="other-comments">
         <h1 class="title other-comments-header">
          <%- otherReviewsText %>
         </h1>
         <ul></ul>
        </div>
        <form method="post">
         <h1 class="comment-dlg-header">
          <span class="title"></span>
          <% if (canEdit) { %>
           <a class="markdown-info" href="<%- markdownDocsURL %>"
              target="_blank"><%- markdownText %></a>
          <% } %>
         </h1>
         <% if (!authenticated) { %>
          <p class="login-text"><%= loginText %></p>
         <% } else if (deletedWarning) { %>
          <p class="deleted-warning"><%= deletedWarning %></p>
         <% } else if (readOnly) { %>
          <p class="read-only-text"><%= readOnlyText %></p>
         <% } else if (draftWarning) { %>
          <p class="draft-warning"><%= draftWarning %></p>
         <% } %>
         <div class="comment-dlg-body">
          <div class="comment-text-field"></div>
          <ul class="comment-dlg-options">
           <li class="comment-issue-options">
            <input type="checkbox" id="comment_issue">
            <label for="comment_issue"
                   accesskey="i"><%= openAnIssueText %></label>
            <% if (showVerify) { %>
             <input type="checkbox" id="comment_issue_verify">
             <label for="comment_issue_verify"><%= verifyIssueText %></label>
            <% } %>
           </li>
           <li class="comment-markdown-options">
            <input type="checkbox" id="enable_markdown">
            <label for="enable_markdown"
                   accesskey="m"><%= enableMarkdownText %></label>
           </li>
          </ul>
         </div>
         <div class="comment-dlg-footer">
          <div class="buttons">
           <button class="ink-c-button btn-save" type="button" disabled>
            <%- saveButton %>
           </button>
           <button class="ink-c-button btn-cancel" type="button">
            <%- cancelButton %>
           </button>
           <button class="ink-c-button btn-delete" type="button" disabled>
            <%- deleteButton %>
           </button>
           <button class="ink-c-button btn-close" type="button">
            <%- closeButton %>
           </button>
          </div>
         </div>
        </form>
    `);

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
     *     options (CommentDialogViewCreationOptions):
     *         Options for the view construction.
     */
    static create(
        options: CommentDialogViewCreationOptions,
    ): CommentDialogView {
        console.assert(options.comment, 'A comment must be specified');

        const reviewRequestEditor =
            options.reviewRequestEditor ||
            RB.PageManager.getPage().model.reviewRequestEditor;

        options.animate = (options.animate !== false);

        const dlg = new this({
            animate: options.animate,
            commentIssueManager: (
                options.commentIssueManager ||
                reviewRequestEditor.get('commentIssueManager')),
            deletedWarning: options.deletedWarning,
            draftWarning: options.draftWarning,
            model: new CommentEditor({
                comment: options.comment,
                publishedComments: options.publishedComments || undefined,
                publishedCommentsType: options.publishedCommentsType ||
                                       undefined,
                reviewRequest: reviewRequestEditor.get('reviewRequest'),
                reviewRequestEditor: reviewRequestEditor,
            }),
        });

        dlg.render().$el
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

        dlg.on('closed', () => CommentDialogView._instance = null);

        const instance = CommentDialogView._instance;
        const showCommentDlg = function showCommentDlg() {
            try {
                dlg.open();
            } catch(e) {
                dlg.close();
                throw e;
            }

            CommentDialogView._instance = dlg;
        };

        if (instance) {
            instance.on('closed', showCommentDlg);
            instance.close();
        } else {
            showCommentDlg();
        }

        return dlg;
    }

    /**********************
     * Instance variables *
     **********************/

    /** The buttons on the dialog. */
    $buttons: JQuery;

    /** The cancel button. */
    $cancelButton: JQuery;

    /** The close button. */
    $closeButton: JQuery;

    /** The delete button. */
    $deleteButton: JQuery;

    /** The save button. */
    $saveButton: JQuery;

    /** The list of views for all the comments. */
    commentsList: CommentsListView;

    /** The options for the view. */
    options: CommentDialogViewOptions;

    _$body: JQuery;
    _$commentOptions: JQuery;
    _$commentsPane: JQuery;
    _$draftForm: JQuery;
    _$enableMarkdownField: JQuery;
    _$footer: JQuery;
    _$header: JQuery;
    _$issueField: JQuery;
    _$issueOptions: JQuery;
    _$issueVerificationField: JQuery;
    _$markdownOptions: JQuery;
    _$title: JQuery;
    _textEditor: TextEditorView;
    #$draftWarning;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (CommentDialogViewOptions):
     *         Options for the view.
     */
    initialize(options: CommentDialogViewOptions) {
        this.options = options;
    }

    /**
     * Render the view.
     */
    protected onInitialRender() {
        const model = this.model;
        const userSession = UserSession.instance;
        const reviewRequest = model.get('reviewRequest');
        const reviewRequestEditor = model.get('reviewRequestEditor');
        const deletedWarning = this.options.deletedWarning;

        if (deletedWarning) {
            /* Block commenting on deleted objects. */
            model.set('canEdit', false);
        }

        this.$el
            .hide()
            .html(CommentDialogView.template({
                authenticated: userSession.get('authenticated'),
                canEdit: model.get('canEdit'),
                cancelButton: CommentDialogView._cancelText,
                closeButton: CommentDialogView._closeText,
                deleteButton: CommentDialogView._deleteText,
                deletedWarning: deletedWarning,
                draftWarning: this.options.draftWarning,
                enableMarkdownText: CommentDialogView._enableMarkdownText,
                loginText: interpolate(
                    CommentDialogView._loginTextTemplate,
                    [userSession.get('loginURL')]),
                markdownDocsURL: MANUAL_URL + 'users/markdown/',
                markdownText: CommentDialogView._markdownText,
                openAnIssueText: CommentDialogView._openAnIssueText,
                otherReviewsText: CommentDialogView._otherReviewsText,
                readOnly: userSession.get('readOnly'),
                readOnlyText: _`Review Board is currently in read-only mode.`,
                saveButton: CommentDialogView._saveText,
                showVerify: EnabledFeatures.issueVerification,
                verifyIssueText: CommentDialogView._verifyIssueText,
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
                .bindVisibility(model, 'canEdit');
        this._$markdownOptions =
            this._$commentOptions.children('.comment-markdown-options')
                .bindVisibility(model, 'canEdit');

        this._$issueField = this._$issueOptions
            .find('#comment_issue')
                .bindProperty('checked', model, 'openIssue')
                .bindProperty('disabled', model, 'editing', {
                    elementToModel: false,
                    inverse: true,
                });

        this._$issueVerificationField = this._$issueOptions
            .find('#comment_issue_verify')
                .bindProperty('checked', model, 'requireVerification')
                .bindProperty('disabled', model, 'editing', {
                    elementToModel: false,
                    inverse: true,
                });

        this._$enableMarkdownField = this._$markdownOptions
            .find('#enable_markdown')
                .bindProperty('checked', model, 'richText')
                .bindProperty('disabled', model, 'editing', {
                    elementToModel: false,
                    inverse: true,
                });

        this.#$draftWarning = this.$('.draft-warning');

        const $buttons = this._$footer.find('.buttons');
        this.$buttons = $buttons;

        this.$saveButton = $buttons.children('.btn-save')
            .bindVisibility(model, 'canEdit')
            .bindProperty('disabled', model, 'canSave', {
                elementToModel: false,
                inverse: true,
            });

        this.$cancelButton = $buttons.children('.btn-cancel')
            .bindVisibility(model, 'canEdit');

        this.$deleteButton = $buttons.children('.btn-delete')
            .bindVisibility(model, 'canDelete')
            .bindProperty('disabled', model, 'canDelete', {
                elementToModel: false,
                inverse: true,
            });

        this.$closeButton = $buttons.children('.btn-close')
            .bindVisibility(model, 'canEdit', {
                inverse: true,
            });

        this.commentsList = new CommentsListView({
            commentIssueManager: this.options.commentIssueManager,
            el: this._$commentsPane.find('ul'),
            issuesInteractive: reviewRequestEditor.get('editable'),
            reviewRequestURL: reviewRequest.get('reviewURL'),
        });

        /*
         * We need to handle keypress here, rather than in events above,
         * because jQuery will actually handle it. Backbone fails to.
         */
        this._textEditor = new TextEditorView({
            autoSize: false,
            bindRichText: {
                attrName: 'richText',
                model: model,
            },
            el: this._$draftForm.find('.comment-text-field'),
            minHeight: 0,
            text: model.get('text'),
        });
        this._textEditor.render();
        this._textEditor.show();
        this._textEditor.$el.bindVisibility(model, 'canEdit');
        this.listenTo(this._textEditor, 'change',
                      () => model.set('text',
                                           this._textEditor.getText()));
        this._textEditor.bindRichTextCheckbox(this._$enableMarkdownField);
        this._textEditor.bindRichTextVisibility(
            this._$draftForm.find('.markdown-info'));

        this.listenTo(model, 'change:text',
                      () => this._textEditor.setText(model.get('text')));

        this.listenTo(model, 'change:richText', this.#handleResize);

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
                resize: _.bind(this.#handleResize, this),
                transparent: true,
            })
            .proxyTouchEvents();

        this.$el.draggable({
            handle:  '.comment-dlg-header, .other-comments-header',
        });

        this.listenTo(model, 'change:dirty', this.#updateTitle);
        this.#updateTitle();

        this.listenTo(model, 'change:publishedComments',
                      () => this.#onPublishedCommentsChanged());
        this.#onPublishedCommentsChanged();

        /* Add any hooks. */
        CommentDialogHook.each(hook => {
            const HookViewType = hook.get('viewType');
            const hookView = new HookViewType({
                commentDialog: this,
                commentEditor: model,
                el: this.el,
                extension: hook.get('extension'),
            });

            hookView.render();
        });
    }

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
            this.model.save()
                .catch(err => {
                    alert(_`Error saving comment: ` + err.message);
                });

            this.close();
        }
    }

    /**
     * Open the comment dialog and focuses the text field.
     */
    open() {
        function openDialog() {
            this.$el.scrollIntoView();
            this._textEditor.focus();
        }

        if (this.options.animate) {
            this.$el.css({
                opacity: 0,
                top: (parseInt(this.$el.css('top'), 10) -
                      CommentDialogView.SLIDE_DISTANCE),
            });
        }

        this.$el.show();

        this.#handleResize();

        if (this.model.get('canEdit')) {
            this.model.beginEdit();
        }

        if (this.options.animate) {
            this.$el.animate({
                opacity: 1,
                top: `+=${CommentDialogView.SLIDE_DISTANCE}px`,
            }, 350, 'swing', _.bind(openDialog, this));
        } else {
            openDialog.call(this);
        }
    }

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
                opacity: 0,
                top: `-=${CommentDialogView.SLIDE_DISTANCE}px`,
            }, 350, 'swing', _.bind(closeDialog, this));
        } else {
            closeDialog.call(this);
        }
    }

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
    }

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
    }

    /**
     * Update the title of the comment dialog, based on the current state.
     */
    #updateTitle() {
        this._$title.text(this.model.get('dirty')
                          ? CommentDialogView._yourCommentDirtyText
                          : CommentDialogView._yourCommentText);
    }

    /**
     * Callback for when the list of published comments changes.
     *
     * Sets the list of comments in the CommentsList, and factors in some
     * new layout properties.
     */
    #onPublishedCommentsChanged() {
        const comments = this.model.get('publishedComments') || [];
        this.commentsList.setComments(
            comments, this.model.get('publishedCommentsType'));

        const showComments = (comments.length > 0);
        const canFitPortraitMode = this.#canFitPortraitMode();
        this._$commentsPane.toggle(showComments);

        /* Do this here so that calculations can be done before open() */
        let width = CommentDialogView.FORM_BOX_WIDTH;
        let height = CommentDialogView.DIALOG_NON_EDITABLE_HEIGHT;

        if (showComments && !canFitPortraitMode) {
            width += CommentDialogView.COMMENTS_BOX_WIDTH;
        }

        if (showComments && canFitPortraitMode) {
            height = CommentDialogView.DIALOG_TOTAL_HEIGHT_PORTRAIT;
        } else if (this.model.get('canEdit')) {
            height = CommentDialogView.DIALOG_TOTAL_HEIGHT;
        } else if (UserSession.instance.get('readOnly')) {
            height = CommentDialogView.DIALOG_READ_ONLY_HEIGHT;
        }

        this.$el
            .width(width)
            .height(height);
    }

    /**
     * Handle the resize of the comment dialog.
     *
     * This will lay out the elements in the dialog appropriately.
     */
    #handleResize() {
        const showComments = this._$commentsPane.is(':visible');
        let height = this.$el.height();
        let width = this.$el.width();
        let draftFormX = 0;
        let draftFormY = 0;

        if (showComments) {
            let commentsHeight = height;
            let commentsWidth = width;

            if (this.#canFitPortraitMode()) {
                /*
                 * Portrait mode, stack the comments box and draft form
                 * vertically.
                 */
                commentsHeight =
                    CommentDialogView.COMMENTS_BOX_HEIGHT_PORTRAIT;
                draftFormY = commentsHeight;
                height -= commentsHeight;
            } else {
                /*
                 * Landscape mode, stack the comments box and draft form
                 * horizontally.
                 */
                commentsWidth = CommentDialogView.COMMENTS_BOX_WIDTH;
                draftFormX = commentsWidth;
                width -= commentsWidth;
            }

            this._$commentsPane
                .outerWidth(commentsWidth)
                .outerHeight(commentsHeight)
                .move(0, 0, 'absolute');
            const $commentsList = this.commentsList.$el;
            $commentsList.height(this._$commentsPane.height() -
                                 $commentsList.position().top);
        }

        this._$draftForm
            .outerWidth(width)
            .outerHeight(height)
            .move(draftFormX, draftFormY, 'absolute');

        const warningHeight = this.#$draftWarning.outerHeight(true) || 0;

        const $textField = this._textEditor.$el;
        this._textEditor.setSize(
            (this._$body.width() -
             $textField.getExtents('b', 'lr')),
            (this._$draftForm.height() -
             this._$header.outerHeight() -
             this._$commentOptions.outerHeight() -
             this._$footer.outerHeight() -
             warningHeight -
             $textField.getExtents('b', 'tb')));
    }

    /**
     * Return whether the portrait version of the dialog can fit on screen.
     *
     * This checks whether the height of the dialog fits within the screen
     * height.
     *
     * Version Added:
     *     7.0.3
     *
     * Returns:
     *     boolean:
     *     Whether the portrait version of the dialog can fit on screen.
     */
    #canFitPortraitMode(): boolean {
        return (
            RB.PageManager.getPage().inMobileMode &&
            $(window).height() > CommentDialogView.DIALOG_TOTAL_HEIGHT_PORTRAIT
        );
    }

    /**
     * Callback for when the Cancel button is pressed.
     *
     * Cancels the comment (which may delete the comment block, if it's new)
     * and closes the dialog.
     */
    _onCancelClicked() {
        let shouldExit = true;

        if (this.model.get('dirty')) {
            shouldExit = confirm(CommentDialogView._shouldExitText);
        }

        if (shouldExit) {
            this.model.cancel();
            this.close();
        }
    }

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
    }

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
     *     e (KeyboardEvent):
     *         The keydown event.
     */
    _onTextKeyDown(e: KeyboardEvent) {
        if (e.key === 'Escape') {
            e.preventDefault();
            e.stopPropagation();

            this._onCancelClicked();
        } else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            e.stopPropagation();

            this.save();
        } else if (e.key === 'i' && (e.metaKey || e.altKey)) {
            e.preventDefault();
            e.stopPropagation();

            this.model.set('openIssue', !this.model.get('openIssue'));
        } else if (e.key === 'm' && (e.metaKey || e.altKey)) {
            e.preventDefault();
            e.stopPropagation();

            this.model.set('richText', !this.model.get('richText'));
        }
    }

    /**
     * Callback for scroll or wheel events.
     *
     * This will prevent the page from scrolling when the scroll wheel is
     * used over the comment dialog.
     *
     * Version Added:
     *     7.0
     *
     * Args:
     *     evt (Event):
     *         The scroll or wheel event.
     */
    _onScroll(evt: Event) {
        const target = evt.target as HTMLElement;
        let textEl: HTMLElement = null;

        if (target.tagName === 'TEXTAREA' ||
            target.classList.contains('CodeMirror-scroll')) {
            textEl = target;
        } else {
            textEl = target.closest('.CodeMirror-scroll');
        }

        if (textEl === null) {
            /*
             * If the event is happening in the comment dialog but not in the
             * text editor or Other Comments area, we can just swallow it
             * right away.
             */
            if (target.closest('.other-comments > ul') === null) {
                evt.preventDefault();
            }
        } else {
            /*
             * If the event is in the text editor, we need to figure out if the
             * editor is scrollable. If it is, we let the default handler run.
             * If not, swallow it so it doesn't bubble up to the main
             * document.
             */
            if (textEl.scrollHeight === textEl.clientHeight) {
                evt.preventDefault();
            }
        }
    }
}
