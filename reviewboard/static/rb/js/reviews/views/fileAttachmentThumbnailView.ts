/**
 * The file attachment thumbnail view.
 */

import { BaseView, spina } from '@beanbag/spina';

import {
    FileAttachment,
    FileAttachmentStates,
} from 'reviewboard/common';
import {
    FieldStateLabelThemes,
    FieldStateLabelView,
    InlineEditorView,
} from 'reviewboard/ui';

import { ReviewRequestEditor } from '../models/reviewRequestEditorModel';
import { CommentDialogView } from './commentDialogView';


/**
 * Options for the FileAttachmentThumbnailView.
 *
 * Version Added:
 *     6.0
 */
interface FileAttachmentThumbnailViewOptions {
    /** The review request model. */
    reviewRequest: RB.ReviewRequest;

    /** The review request editor. */
    reviewRequestEditor: ReviewRequestEditor;

    /** Whether the user has permission to edit the file attachment. */
    canEdit?: boolean;

    /** The comments on the file attachment. */
    comments?: RB.FileAttachmentComment[];

    /**
     * Whether the thumbnail should be rendered.
     *
     * This exists because we sometimes attach to existing DOM elements
     * rather than rendering from scratch.
     */
    renderThumbnail?: boolean;
}


/**
 * Displays a thumbnail depicting a file attachment.
 *
 * There are two ways that Review Board currently renders file attachments.
 * One is on page load (as part of the initial page template), and the other
 * is dynamically (when uploading vs Drag and Drop or manual upload).
 *
 * Depending on the method, we either already have elements to work with,
 * or we don't. In the latter case, it's currently up to the caller to
 * tell us, using the renderThumbnail option.
 *
 * File attachments that aren't already on the page that are currently loading
 * will be displayed as a blank file attachment (no identifying information)
 * with a spinner. When loaded, it will appear as a standard file attachment.
 *
 * The following signals are provided, on top of the standard Backbone.View
 * signals:
 *
 *     * beginEdit
 *       - Editing of the file attachment (caption) has begun.
 *
 *     * endEdit
 *       - Editing of the file attachment (caption) has finished.
 *
 *     * commentSaved
 *       - A draft comment on the file has been saved.
 *         (Only for file attachments without a Review UI.)
 *
 * Version Changed:
 *     6.0:
 *     Deprecated the ``FileAttachmentThumbnail`` name for this view and
 *     renamed to ``FileAttachmentThumbnailView``.
 */
@spina({
    prototypeAttrs: [
        'actionsTemplate',
        'states',
        'template',
        'thumbnailContainerTemplate',
    ],
})
export class FileAttachmentThumbnailView extends BaseView<
    FileAttachment,
    HTMLDivElement,
    FileAttachmentThumbnailViewOptions
> {
    static className = 'file-container';

    static events = {
        'click .file-add-comment a': '_onAddCommentClicked',
        'click .file-delete': '_onDeleteClicked',
        'click .file-undo-delete': '_onUndoDeleteClicked',
        'click .file-update a': '_onUpdateClicked',
    };

    static template = _.template(dedent`
        <div class="file">
         <div class="file-actions-container">
          <ul class="file-actions"></ul>
         </div>
         <div class="file-state-container"></div>
         <div class="file-thumbnail-container"></div>
         <div class="file-caption-container">
          <div class="file-caption can-edit">
           <a href="<%- downloadURL %>" class="<%- captionClass %>">
            <%- caption %>
           </a>
          </div>
         </div>
        </div>
    `);

    static actionsTemplate = _.template(dedent`
        <% if (loaded) { %>
        <%  if (canReview) { %>
        <%   if (reviewURL) { %>
        <li>
         <a class="file-review" role="button" href="<%- reviewURL %>">
          <span class="fa fa-comment-o" aria-hidden="true"></span>
          <%- reviewText %>
         </a>
        </li>
        <%   } else { %>
        <li class="file-add-comment">
         <a role="button" href="#">
          <span class="fa fa-comment-o" aria-hidden="true"></span>
          <%- commentText %>
         </a>
        </li>
        <%   } %>
        <%  } %>
        <li>
         <a class="file-download" role="button" href="<%- downloadURL %>">
          <span class="fa fa-download" aria-hidden="true"></span>
          <%- downloadText %>
         </a>
        </li>
        <%  if (canUndoDeletion) { %>
            <li class="file-undo-delete">
             <a role="button" href="#">
              <span class="fa fa-undo" aria-hidden="true"></span>
              <%- undoDeleteText %>
             </a>
            </li>
        <%  } else if (canEdit) { %>
        <%   if (attachmentHistoryID) { %>
        <li class="file-update">
         <a role="button" href="#"
            data-attachment-history-id="<%- attachmentHistoryID %>">
          <span class="fa fa-upload" aria-hidden="true"></span>
          <%- updateText %>
         </a>
        </li>
        <%   } %>
        <li class="file-delete">
         <a role="button" href="#">
          <span class="fa fa-trash-o" aria-hidden="true"></span>
          <%- deleteText %>
         </a>
        </li>
        <%  } %>
        <% } %>
    `);

    static thumbnailContainerTemplate = _.template(dedent`
        <% if (!loaded) { %>
        <span class="djblets-o-spinner"></span>
        <% } else { %>
        <%     if (reviewURL) { %>
        <a href="<%- reviewURL %>" class="file-thumbnail-overlay"></a>
        <%     } %>
        <%=  thumbnailHTML %>
        <% } %>
    `);

    /** The possible states for the file attachment. */
    static states = FileAttachmentStates;

    /**********************
     * Instance variables *
     **********************/

    /** The view options. */
    options: FileAttachmentThumbnailViewOptions;

    /**
     * The file actions.
     *
     * This is only public so that it can be accessed in unit tests.
     */
    _$actions: JQuery;

    /**
     * The view for editing the caption.
     *
     * This is only public so that it can be accessed in unit tests.
     */
    _captionEditorView: InlineEditorView;

    /** The file actions container. */
    #$actionsContainer: JQuery;

    /** The caption. */
    #$caption: JQuery;

    /** The caption container. */
    #$captionContainer: JQuery;

    /** The element representing the whole file attachment. */
    #$file: JQuery;

    /** The container for the state label. */
    #$stateContainer: JQuery;

    /** The thumbnail container. */
    #$thumbnailContainer: JQuery;

    /**
     * Whether the user can currently edit the file attachment.
     *
     * This differs from options.canEdit because this may change depending
     * on the file attachment state.
     */
    #canCurrentlyEdit: boolean;

    /** The processed comments that are usable in the comment dialog. */
    #comments: RB.FileAttachmentComment[] = [];

    /** Whether the comments have been processed. */
    #commentsProcessed: boolean = null;

    /** The current draft comment for the file attachment. */
    #draftComment: RB.FileAttachmentComment = null;

    /** Whether the thumbnail supports scrolling. */
    #scrollingThumbnail: boolean = null;

    /** The view for the state label. */
    #stateLabelView: FieldStateLabelView;

    /** Whether the thumbnail is currently playing a video. */
    #playingVideo: boolean = null;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (FileAttachmentThumbnailViewOptions):
     *         Options for the view.
     */
    initialize(options: FileAttachmentThumbnailViewOptions) {
        this.options = options;
        this.#canCurrentlyEdit = (
            this.model.get('state') !== this.states.PENDING_DELETION &&
            options.canEdit);
    }

    /**
     * Render the file attachment, and hooks up all events.
     *
     * If the renderThumbnail option was provided when constructing the view,
     * this will render the thumbnail from scratch, and then dynamically
     * update it as it loads. It will start off displaying with a spinner,
     * if not yet loaded.
     *
     * In either case, this will set up the caption editor and other signals
     * to control the lifetime of the thumbnail.
     */
    onInitialRender() {
        /*
         * Until FileAttachmentThumbnailView is the only thing rendering
         * thumbnails, we'll be in a situation where we may either be working
         * with an existing DOM element (for existing file attachments), or a
         * new one (for newly uploaded file attachments). In the latter case,
         * we'll want to render our own thumbnail.
         */
        if (this.options.renderThumbnail) {
            this._renderContents();
        }

        this.#$captionContainer = this.$('.file-caption');
        this.#$caption = this.#$captionContainer.find('a.edit');

        this.listenTo(this.model, 'destroy', () => {
            this.$el.fadeOut(() => this.remove());
        });

        this.listenTo(this.model, 'change:caption', this._onCaptionChanged);
        this._onCaptionChanged();

        this.$el.hover(this._onHoverIn.bind(this),
                       this._onHoverOut.bind(this));

        if (this.options.renderThumbnail) {
            this.#$actionsContainer = this.$('.file-actions-container');
            this._$actions = this.#$actionsContainer.children('.file-actions');
            this.#$captionContainer = this.$('.file-caption-container');
            this.#$thumbnailContainer = this.$('.file-thumbnail-container');
            this.#$stateContainer = this.$('.file-state-container');
            this.#$file = this.$('.file');

            this._$actions.find('.file-download')
                .bindProperty('href', this.model, 'downloadURL', {
                    elementToModel: false,
                });

            this.#$caption.bindProperty('href', this.model, 'downloadURL', {
                elementToModel: false,
            });

            this.listenTo(this.model, 'change:loaded', this._onLoadedChanged);
            this._onLoadedChanged();

            this.listenTo(this.model, 'change:thumbnailHTML',
                          this._renderThumbnail);
            this._renderThumbnail();

            this.listenTo(this.model, 'change:state', this._onStateChanged);
            this._renderStateLabel();
        }

        this._renderCaptionEditor();


        if (!this.options.renderThumbnail) {
            /*
             * Add any hooks. If renderThumbnail is true then the hooks will
             * have already been added.
            */
            RB.FileAttachmentThumbnailContainerHook.each(hook => {
                const HookViewType = hook.get('viewType');
                const hookView = new HookViewType({
                    el: this.el,
                    extension: hook.get('extension'),
                    fileAttachment: this.model,
                    thumbnailView: this,
                });

                hookView.render();
            });
        }
    }

    /**
     * Fade the view in.
     */
    fadeIn() {
        this.$el
            .css('opacity', 0)
            .fadeTo(1000, 1);
    }

    /**
     * Add a new action to the actions menu.
     *
     * Args:
     *     appendToClass (str):
     *         The class of an existing action item for which the new
     *         action item will follow. In the actions menu list, the
     *         new action will appear as the next item after this action.
     *
     *     itemClass (str):
     *         The class of the new action, to set on the list element
     *         that wraps the action. If an action of this class already
     *         exists, it will be removed and replaced by this new action.
     *
     *     itemHTML (str):
     *         The HTML of the new action item.
     *
     * Returns:
     *     jQuery:
     *     The element of the new action item.
     */
    addAction(
        appendToClass: string,
        itemClass: string,
        itemHTML: string,
    ): JQuery {
        this._$actions.find(`.${itemClass}`).remove();

        const itemTemplate = _.template(dedent`
            <li class="<%= itemClass %>">
             <%=  itemHTML %>
            </li>
        `);
        const $appendItem = this._$actions
            .find(`.${appendToClass}`).closest('li');

        const $action = $(itemTemplate({
            itemClass: itemClass,
            itemHTML: itemHTML,
        }));

        $appendItem.after($action);

        return $action;
    }

    /**
     * Show the comment dialog for the file attachment.
     *
     * This is only ever used if the file attachment does not have a
     * Review UI for it. A single comment dialog will appear, allowing
     * comments on the file as a whole.
     */
    showCommentDlg() {
        console.assert(!this.model.get('reviewURL'),
                       'showCommentDlg can only be called if the file ' +
                       'attachment does not have a review UI');
        this._processComments();
        this._createDraftComment();

        CommentDialogView.create({
            comment: this.#draftComment,
            position: {
                beside: {
                    el: this.$el,
                    fitOnScreen: true,
                    side: 'br',
                },
            },
            publishedComments: this.#comments,
            publishedCommentsType: 'file_attachment_comments',
        });
    }

    /**
     * Process all comments provided when constructing the view.
     *
     * The comments will be made usable by the comment dialog.
     *
     * This is only used if the file attachment does not have a Review UI.
     */
    _processComments() {
        if (this.#commentsProcessed) {
            return;
        }

        const comments = this.options.comments || [];

        comments.forEach(comment => {
            if (comment.localdraft) {
                this._createDraftComment(comment.comment_id, comment.text);
            } else {
                this.#comments.push(comment);
            }
        });

        this.#commentsProcessed = true;
    }

    /**
     * Create a new draft comment with the given ID and text.
     *
     * Only one draft comment can be created at a time.
     *
     * This is only used if the file attachment does not have a Review UI.
     *
     * Args:
     *     commentID (number):
     *         The ID of the draft comment.
     *
     *     text (string):
     *         The comment text.
     */
    _createDraftComment(
        commentID: number,
        text: string,
    ) {
        if (this.#draftComment !== null) {
            return;
        }

        const review = this.options.reviewRequest.createReview();
        this.#draftComment = review.createFileAttachmentComment(commentID,
                                                                this.model.id);

        if (text) {
            this.#draftComment.set('text', text);
        }

        this.listenTo(this.#draftComment, 'saved',
                      () => this.trigger('commentSaved', this.#draftComment));
    }

    /**
     * Save the given caption value.
     *
     * Version Added:
     *     6.0
     */
    async _saveCaption(val: string) {
        const model = this.model;

        /*
         * We want to set the caption after ready() finishes, in case
         * it loads state and overwrites.
         */
        await model.ready();

        model.set('caption', val);
        this.trigger('endEdit');
        await model.save({
            attrs: ['caption'],
        });
    }

    /**
     * Render the caption editor and set up its event listeners.
     *
     * Version Added:
     *     6.0
     */
    _renderCaptionEditor() {
        if (this.#canCurrentlyEdit === false && this._captionEditorView) {
            /*
             * The view exists but we're not allowed to edit anymore.
             * Remove it.
             */
            this._captionEditorView.remove();

            return;
        } else if (this.#canCurrentlyEdit && this._captionEditorView) {
            /* The view already exists. No op. */
            return;
        } else if (this.#canCurrentlyEdit === false) {
            /* The view doesn't and shouldn't exist. No op. */
            return;
        }

        this._captionEditorView = new InlineEditorView({
            editIconClass: 'rb-icon rb-icon-edit',
            el: this.#$caption,
            showButtons: true,
        });

        this._captionEditorView.render();

        this.listenTo(this._captionEditorView, 'beginEditPreShow', () => {
            this.$el.addClass('editing');
            this._stopAnimating();
        });

        this.listenTo(this._captionEditorView, 'beginEdit', () => {
            if (this.#$caption.hasClass('empty-caption')) {
                this._captionEditorView.$field.val('');
            }

            this.trigger('beginEdit');
        });

        this.listenTo(this._captionEditorView, 'cancel', () => {
            this.$el.removeClass('editing');
            this.trigger('endEdit');
        });

        this.listenTo(this._captionEditorView, 'complete', async val => {
            this.$el.removeClass('editing');
            await this._saveCaption(val);
        });
    }

    /**
     * Render the contents of this view's element.
     *
     * This is only done when requested by the caller.
     */
    _renderContents() {
        const model = this.model;
        const caption = model.get('caption');
        const captionText = caption ? caption : _`No caption`;
        const captionClass = caption ? 'edit' : 'edit empty-caption';

        this.$el
            .html(this.template(_.defaults({
                caption: captionText,
                captionClass: captionClass,
            }, model.attributes)))
            .addClass(this.className);
    }

    /**
     * Render the thumbnail for the file attachment.
     */
    _renderThumbnail() {
        this.#$thumbnailContainer.html(
            this.thumbnailContainerTemplate(this.model.attributes));

        Djblets.enableRetinaImages(this.#$thumbnailContainer);

        // Disable tabbing to any <a> elements inside the thumbnail.
        this.#$thumbnailContainer.find('a').each((i, el) => {
            el.tabIndex = -1;
        });
    }

    /**
     * Render the state label for the file attachment.
     *
     * Version Added:
     *     6.0
     */
    _renderStateLabel() {
        if (this.#stateLabelView) {
            this.#stateLabelView.remove();
        }

        if (!this.options.canEdit) {
            return;
        }

        const state = this.model.get('state');

        if (state === this.states.PUBLISHED ||
            state === this.states.DELETED) {
            /* Don't display state labels for these types of attachments. */
            return;
        }

        const theme = (state === this.states.PENDING_DELETION
                       ? FieldStateLabelThemes.DELETED
                       : FieldStateLabelThemes.DRAFT);

        this.#stateLabelView = new FieldStateLabelView({
            state: this._getStateText(state),
            theme: theme,
        });

        this.#stateLabelView.renderInto(this.#$stateContainer);
    }

    /**
     * Handler for when the model's 'state' property changes.
     *
     * Args:
     *     model (FileAttachment):
     *         The file attachment model.
     *
     *     state (string):
     *         The new state value.
     */
    _onStateChanged(
        model: FileAttachment,
        state: string,
    ) {
        if (state === this.states.PENDING_DELETION) {
            /* Block editing for attachments that are pending deletion. */
            this.#canCurrentlyEdit = false;
        } else if (this.#canCurrentlyEdit !== this.options.canEdit) {
            /* We're not pending deletion, set this back to canEdit. */
            this.#canCurrentlyEdit = this.options.canEdit;
        }

        this._renderStateLabel();
        this._onLoadedChanged();
        this._renderCaptionEditor();
    }

    /**
     * Handler for when the model's 'loaded' property changes.
     *
     * Depending on if the file attachment is now loaded, either a
     * blank spinner thumbnail will be shown, or a full thumbnail.
     */
    _onLoadedChanged() {
        const model = this.model;
        const state = model.get('state');
        const useDraftDelete = (
            state === this.states.NEW ||
            state === this.states.NEW_REVISION ||
            state === this.states.DRAFT
        );
        const deleteText = (useDraftDelete
                            ? _`Delete Draft`
                            : _`Delete`);

        this._$actions.html(this.actionsTemplate(_.defaults({
            canEdit: this.options.canEdit,
            canReview: (state !== this.states.DELETED),
            canUndoDeletion: (state === this.states.PENDING_DELETION &&
                              this.options.canEdit),
            commentText: _`Comment`,
            deleteText: deleteText,
            downloadText: _`Download`,
            reviewText: _`Review`,
            undoDeleteText: _`Undo Delete`,
            updateText: _`Update`,
        }, model.attributes)));

        /*
        * Some hooks may depend on the elements being added above, so
        * render the hooks here too.
        */
        RB.FileAttachmentThumbnailContainerHook.each(hook => {
            const HookViewType = hook.get('viewType');
            const hookView = new HookViewType({
                el: this.el,
                extension: hook.get('extension'),
                fileAttachment: model,
                thumbnailView: this,
            });

            hookView.render();
        });
    }

    /**
     * Handler for when the model's caption changes.
     *
     * If a caption is set, the thumbnail will display it. Otherwise,
     * it will display "No caption".
     */
    _onCaptionChanged() {
        const model = this.model;
        const state = model.get('state');
        const caption = model.get('caption');
        const publishedCaption = model.get('publishedCaption');
        const captionHasChanged = (caption !== publishedCaption);

        if (caption) {
            this.#$caption
                .text(caption)
                .removeClass('empty-caption');
        } else {
            this.#$caption
                .text(_`No caption`)
                .addClass('empty-caption');
        }

        if (state === this.states.DRAFT && !captionHasChanged) {
            /*
             * This is a draft but the caption has changed back to the
             * published version. Remove the draft state.
             */
            model.set('state', this.states.PUBLISHED);
        } else if (state === this.states.PUBLISHED && captionHasChanged) {
            /* The caption changed, put this into draft state. */
            model.set('state', this.states.DRAFT);
        }

    }

    /**
     * Handler for the New Comment button.
     *
     * Shows the comment dialog.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event that triggered the action.
     */
    _onAddCommentClicked(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        this.showCommentDlg();
    }

    /**
     * Handler for the Update button.
     *
     * Shows the upload form.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event that triggered the action.
     */
    _onUpdateClicked(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        const model = this.model;
        const updateDlg = new RB.UploadAttachmentView({
            attachmentHistoryID: model.get('attachmentHistoryID'),
            presetCaption: model.get('caption'),
            reviewRequestEditor: this.options.reviewRequestEditor,
        });
        updateDlg.show();
    }

    /**
     * Handler for the Delete button.
     *
     * Deletes the file attachment from the review request draft.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event that triggered the action.
     */
    async _onDeleteClicked(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        const model = this.model;
        const state = model.get('state');

        if (state === this.states.DRAFT) {
            /*
             * "Delete" the draft version of the file attachment by reverting
             * to its published caption.
             */
            await this._saveCaption(model.get('publishedCaption'));
        } else {
            model.destroy();
        }
    }

    /**
     * Handler for the Undo Delete button.
     *
     * Undoes the pending deletion of the file attachment, reverting it
     * to its published state.
     *
     * Args:
     *     e (JQuery.ClickEvent):
     *         The event that triggered the action.
     */
    _onUndoDeleteClicked(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        const model = this.model;

        RB.apiCall({
            data: {
                'pending_deletion': false,
            },
            error: xhr => {
                const rsp = xhr.responseJSON;
                const caption = model.get('caption');

                if (rsp && rsp.stat) {
                    alert(dedent`Failed to undo the deletion of file attachment
                          "${caption}": ${rsp.err.msg}`);
                } else {
                    alert(dedent`Failed to undo the deletion of file attachment
                          "${caption}": ${xhr.errorText}`);
                }
            },
            method: 'PUT',
            success: () => {
                model.set({
                    state: this.states.PUBLISHED,
                });
            },
            url: model.url(),
        });
    }

    /**
     * Handler for when the mouse hovers over the thumbnail.
     *
     * Determines if we should scroll the thumbnail or not.
     */
    _onHoverIn() {
        const $thumbnail = this.$('.file-thumbnail').children();
        const actionsWidth = this.#$actionsContainer.outerWidth();
        const actionsRight = (this.#$file.offset().left +
                              this.#$file.outerWidth() +
                              actionsWidth);

        this.trigger('hoverIn', this.$el);

        /*
         * Position the actions menu to the left or right of the attachment
         * thumbnail.
         */
        if (actionsRight > $(window).width()) {
            this.#$actionsContainer
                .css('left', -actionsWidth)
                .addClass('left');
        } else {
            this.#$actionsContainer
                .css('left', '100%')
                .addClass('right');
        }

        if (!this.$el.hasClass('editing') && $thumbnail.length === 1) {
            const thumbnailEl = $thumbnail[0];

            if (thumbnailEl.tagName === 'VIDEO') {
                /* The thumbnail contains a video, so start playing it. */
                const promise = thumbnailEl.play();

                if (promise === undefined) {
                    /* Older browsers don't return Promises. */
                    this.#playingVideo = true;
                } else {
                    promise
                        .then(() => {
                            this.#playingVideo = true;
                        })
                        .catch(error => {
                            /* Ignore the error. We just won't play it. */
                            console.error(
                                'Unable to play the video attachment: %s',
                                error);
                        });
                }
            } else {
                /* Scroll the container to show all available content. */
                const elHeight = this.$el.height();
                const thumbnailHeight = $thumbnail.height() || 0;

                if (thumbnailHeight > elHeight) {
                    const distance = elHeight - thumbnailHeight;
                    const duration =
                        (Math.abs(distance) / 200) * 1000; // 200 pixels/s

                    this.#scrollingThumbnail = true;
                    $thumbnail
                        .delay(1000)
                        .animate(
                            { 'margin-top': distance + 'px' },
                            {
                                duration: duration,
                                easing: 'linear',
                            })
                        .delay(500)
                        .animate(
                            { 'margin-top': 0 },
                            {
                                complete: () => {
                                    this.#scrollingThumbnail = false;
                                },
                                duration: duration,
                                easing: 'linear',
                            });
                }
            }
        }
    }

    /**
     * Handler for when the mouse stops hovering over the thumbnail.
     *
     * Removes the classes for the actions container, and stops animating
     * the thumbnail contents.
     */
    _onHoverOut() {
        this.trigger('hoverOut');

        this.#$actionsContainer
            .removeClass('left')
            .removeClass('right');

        this._stopAnimating();
    }

    /**
     * Stop animating this thumbnail.
     *
     * This is when moving the mouse outside of the thumbnail, or when the
     * caption editor is opened.
     */
    _stopAnimating() {
        if (this.#scrollingThumbnail) {
            this.#scrollingThumbnail = false;
            this.$('.file-thumbnail').children()
                .stop(true)
                .animate(
                    { 'margin-top': 0 },
                    { duration: 100 });
        } else if (this.#playingVideo) {
            this.#playingVideo = false;
            this.$('video')[0].pause();
        }
    }

    /**
     * Return a localized text for the file attachment state.
     *
     * Args:
     *     state (string):
     *         The state value.
     *
     * Returns:
     *     string:
     *     The localized and human readable text representing the state.
     */
    _getStateText(state: string): string {
        switch (state) {
            case FileAttachmentStates.DELETED:
                return _`Deleted`;

            case FileAttachmentStates.DRAFT:
                return _`Draft`;

            case FileAttachmentStates.NEW:
                return _`New`;

            case FileAttachmentStates.NEW_REVISION:
                return _`New Revision`;

            case FileAttachmentStates.PENDING_DELETION:
                return _`Pending Deletion`;

            case FileAttachmentStates.PUBLISHED:
                return _`Published`;

            default:
                return '';
        }
    }
}


/**
 * This is a legacy alias for the FileAttachmentThumbnailView.
 *
 * Deprecated:
 *     6.0
 */
export const FileAttachmentThumbnail = FileAttachmentThumbnailView;
