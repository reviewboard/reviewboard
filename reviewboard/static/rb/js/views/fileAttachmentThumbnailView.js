/*
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
 */
RB.FileAttachmentThumbnail = Backbone.View.extend({
    className: 'file-container',

    events: {
        'click .file-delete': '_onDeleteClicked',
        'click .file-add-comment a': '_onAddCommentClicked',
        'click .file-update a': '_onUpdateClicked'
    },

    template: _.template([
        '<div class="file">',
        ' <div class="file-actions-container">',
        '  <ul class="file-actions"></ul>',
        ' </div>',
        ' <div class="file-thumbnail-container"></div>',
        ' <div class="file-caption-container">',
        // spaceless
        '<div class="file-caption can-edit">',
        '<a href="<%- downloadURL %>" class="<%- captionClass %>">',
        '<%- caption %>',
        '</a>',
        '</div>',
        // end spaceless
        ' </div>',
        '</div>'
    ].join('')),

    actionsTemplate: _.template([
        '<% if (loaded) { %>',
        '<%  if (reviewURL) { %>',
        '<li><a class="file-review" href="<%- reviewURL %>">',
        '<span class="fa fa-comment-o"></span> <%- reviewText %></a>',
        '</li>',
        '<%  } else { %>',
        '<li class="file-add-comment">',
        '<a href="#"><span class="fa fa-comment-o"></span> <%- commentText %></a>',
        '</li>',
        '<%  } %>',
        '<li><a class="file-download" href="<%- downloadURL %>">',
        '<span class="fa fa-download"></span> <%- downloadText %>',
        '</a></li>',
        '<%  if (canEdit) { %>',
        '<%   if (attachmentHistoryID) { %>',
        '<li class="file-update">',
        '<a href="#" data-attachment-history-id="<%- attachmentHistoryID %>">',
        '<span class="fa fa-upload"></span> <%- updateText %>',
        '</a></li>',
        '<%   } %>',
        '<li class="file-delete"><a href="#">',
        '<span class="fa fa-trash-o"></span> <%- deleteText %>',
        '</a></li>',
        '<%  } %>',
        '<% } %>'
    ].join('')),

    thumbnailContainerTemplate: _.template([
        '<% if (!loaded) { %>',
        '<span class="fa fa-spinner fa-pulse"></span>',
        '<% } else { %>',
        '<%     if (reviewURL) { %>',
        '<a href="<%- reviewURL %>" class="file-thumbnail-overlay"></a>',
        '<%     } %>',
        '<%=  thumbnailHTML %>',
        '<% } %>'
    ].join('')),

    initialize: function(options) {
        this.options = options;

        this._draftComment = null;
        this._comments = [];
        this._commentsProcessed = false;
        this._scrollingThumbnail = false;
    },

    /*
     * Renders the file attachment, and hooks up all events.
     *
     * If the renderThumbnail option was provided when constructing the view,
     * this will render the thumbnail from scratch, and then dynamically
     * update it as it loads. It will start off displaying with a spinner,
     * if not yet loaded.
     *
     * In either case, this will set up the caption editor and other signals
     * to control the lifetime of the thumbnail.
     */
    render: function() {
        var self = this;

        /*
         * Until FileAttachmentThumbnail is the only thing rendering thumbnails,
         * we'll be in a situation where we may either be working with an
         * existing DOM element (for existing file attachments), or a new one
         * (for newly uploaded file attachments). In the latter case, we'll want
         * to render our own thumbnail.
         */
        if (this.options.renderThumbnail) {
            this._renderContents();
        }

        this._$captionContainer = this.$('.file-caption');
        this._$caption = this._$captionContainer.find('a.edit');

        this.listenTo(this.model, 'destroy', function() {
            this.$el.fadeOut(function() {
                self.remove();
            });
        });

        this.listenTo(this.model, 'change:caption', this._onCaptionChanged);
        this._onCaptionChanged();

        this.$el.hover(_.bind(this._onHoverIn, this),
                       _.bind(this._onHoverOut, this));

        if (this.options.renderThumbnail) {
            this._$actionsContainer = this.$('.file-actions-container');
            this._$actions = this._$actionsContainer.children('.file-actions');
            this._$captionContainer = this.$('.file-caption-container');
            this._$thumbnailContainer = this.$('.file-thumbnail-container');
            this._$file = this.$('.file');

            this._$actions.find('.file-download')
                .bindProperty('href', this.model, 'downloadURL', {
                    elementToModel: false
                });

            this._$caption.bindProperty('href', this.model, 'downloadURL', {
                elementToModel: false
            });

            this.listenTo(this.model, 'change:loaded', this._onLoadedChanged);
            this._onLoadedChanged();

            this.listenTo(this.model, 'change:thumbnailHTML',
                          this._renderThumbnail);
            this._renderThumbnail();
        }

        if (this.options.canEdit !== false) {
            this._$caption
                .inlineEditor({
                    editIconClass: 'rb-icon rb-icon-edit',
                    showButtons: true
                })
                .on({
                    beginEditPreShow: function() {
                        self.$el.addClass('editing');
                        self._stopAnimating();
                    },
                    beginEdit: function() {
                        var $this = $(this);

                        if ($this.hasClass('empty-caption')) {
                            $this.inlineEditor('field').val('');
                        }

                        self.trigger('beginEdit');
                    },
                    cancel: function() {
                        self.$el.removeClass('editing');
                        self.trigger('endEdit');
                    },
                    complete: function(e, value) {
                        self.$el.removeClass('editing');

                        /*
                         * We want to set the caption after ready() finishes,
                         * it case it loads state and overwrites.
                         */
                        self.model.ready({
                            ready: function() {
                                self.model.set('caption', value);
                                self.trigger('endEdit');
                                self.model.save({
                                    attrs: ['caption']
                                });
                            }
                        });
                    }
                });
        }

        return this;
    },

    fadeIn: function() {
        this.$el
            .css('opacity', 0)
            .fadeTo(1000, 1);
    },

    /*
     * Shows the comment dialog for the file attachment.
     *
     * This is only ever used if the file attachment does not have a
     * Review UI for it. A single comment dialog will appear, allowing
     * comments on the file as a whole.
     */
    showCommentDlg: function() {
        console.assert(!this.model.get('reviewURL'),
                       'showCommentDlg can only be called if the file ' +
                       'attachment does not have a review UI');
        this._processComments();
        this._createDraftComment();

        RB.CommentDialogView.create({
            comment: this._draftComment,
            publishedComments: this._comments,
            publishedCommentsType: 'file_attachment_comments',
            position: {
                beside: {
                    el: this.$el,
                    side: 'br',
                    fitOnScreen: true
                }
            }
        });
    },

    /*
     * Processes all comments provided when constructing the view.
     *
     * The comments will be made usable by the comment dialog.
     *
     * This is only used if the file attachment does not have a Review UI.
     */
    _processComments: function() {
        var comments = this.options.comments || [],
            len = comments.length,
            comment,
            i;

        if (this._commentsProcessed) {
            return;
        }

        for (i = 0; i < len; i++) {
            comment = comments[i];

            if (comment.localdraft) {
                this._createDraftComment(comment.comment_id, comment.text);
            } else {
                this._comments.push(comment);
            }
        }

        this._commentsProcessed = true;
    },

    /*
     * Creates a new draft comment with the given ID and text.
     *
     * Only one draft comment can be created at a time.
     *
     * This is only used if the file attachment does not have a Review UI.
     */
    _createDraftComment: function(commentID, text) {
        var review;

        if (this._draftComment !== null) {
            return;
        }

        review = this.options.reviewRequest.createReview();
        this._draftComment = review.createFileAttachmentComment(commentID,
                                                                this.model.id);

        if (text) {
            this._draftComment.set('text', text);
        }

        this._draftComment.on('saved', function() {
            this.trigger('commentSaved', this._draftComment);
        }, this);
    },

    /*
     * Renders the contents of this view's element.
     *
     * This is only done when requested by the caller.
     */
    _renderContents: function() {
        var caption = this.model.get('caption'),
            captionText = caption ? caption : gettext('No caption'),
            captionClass = caption ? 'edit' : 'edit empty-caption';

        this.$el
            .html(this.template(_.defaults({
                caption: captionText,
                captionClass: captionClass
            }, this.model.attributes)))
            .addClass(this.className);
    },

    /*
     * Renders the thumbnail for the file attachment.
     */
    _renderThumbnail: function() {
        this._$thumbnailContainer.html(
            this.thumbnailContainerTemplate(this.model.attributes));

        _.each(this._$thumbnailContainer.find('img'), function(el) {
            if (el.hasAttribute('data-at2x')) {
                this._retinaImage = new RetinaImage(el);
                el.removeAttribute('data-at2x');
            }
        }, this);

        // Disable tabbing to any <a> elements inside the thumbnail.
        this._$thumbnailContainer.find('a').each(function() {
            this.tabIndex = -1;
        });
    },

    /*
     * Handler for when the model's 'loaded' property changes.
     *
     * Depending on if the file attachment is now loaded, either a
     * blank spinner thumbnail will be shown, or a full thumbnail.
     */
    _onLoadedChanged: function() {
        this._$actions.html(this.actionsTemplate(_.defaults({
            canEdit: this.options.canEdit,
            deleteText: gettext('Delete'),
            downloadText: gettext('Download'),
            reviewText: gettext('Review'),
            commentText: gettext('Comment'),
            updateText: gettext('Update')
        }, this.model.attributes)));
    },

    /*
     * Handler for when the model's caption changes.
     *
     * If a caption is set, the thumbnail will display it. Otherwise,
     * it will display "No caption".
     */
    _onCaptionChanged: function() {
        var caption = this.model.get('caption');

        if (caption) {
            this._$caption
                .text(caption)
                .removeClass('empty-caption');
        } else {
            this._$caption
                .text(gettext('No caption'))
                .addClass('empty-caption');
        }
    },

    /*
     * Handler for the New Comment button.
     *
     * Shows the comment dialog.
     */
    _onAddCommentClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this.showCommentDlg();
    },

    /*
     * Handler for the Update button.
     *
     * Shows the upload form.
     */
    _onUpdateClicked: function(e) {
        var updateDlg;

        e.preventDefault();
        e.stopPropagation();

        updateDlg = new RB.UploadAttachmentView({
            attachmentHistoryID: $(e.target).data('attachment-history-id'),
            presetCaption: this.model.get('caption'),
            reviewRequest: this.options.reviewRequest
        });
        updateDlg.render();
    },

    /*
     * Handler for the Delete button.
     *
     * Deletes the file attachment from the review request draft.
     */
    _onDeleteClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this.model.destroy();
    },

    /*
     * Handler for when the mouse hovers over the thumbnail.
     *
     * Determines if we should scroll the thumbnail or not.
     */
    _onHoverIn: function() {
        var $thumbnail = this.$('.file-thumbnail').children(),
            actionsWidth = this._$actionsContainer.outerWidth(),
            actionsRight = this._$file.offset().left +
                           this._$file.outerWidth() +
                           actionsWidth,
            elHeight,
            thumbnailHeight,
            distance,
            duration;

        this.trigger('hoverIn', this.$el);

        /*
         * Position the actions menu to the left or right of the attachment
         * thumbnail.
         */
        if (actionsRight > $(window).width()) {
            this._$actionsContainer
                .css('left', -actionsWidth)
                .addClass('left');
        } else {
            this._$actionsContainer
                .css('left', '100%')
                .addClass('right');
        }

        if (!this.$el.hasClass('editing') && $thumbnail.length === 1) {
            elHeight = this.$el.height();
            thumbnailHeight = $thumbnail.height() || 0;

            if (thumbnailHeight > elHeight) {
                distance = elHeight - thumbnailHeight;
                duration = (Math.abs(distance) / 200) * 1000; // 200 pixels/s

                this._scrollingThumbnail = true;
                $thumbnail
                    .delay(1000)
                    .animate(
                        { 'margin-top': distance + 'px' },
                        {
                            duration: duration,
                            easing: 'linear'
                        })
                    .delay(500)
                    .animate(
                        { 'margin-top': 0 },
                        {
                            duration: duration,
                            easing: 'linear',
                            complete: _.bind(function() {
                                this._scrollingThumbnail = false;
                            }, this)
                        });
            }
        }
    },

    /*
     * Handler for when the mouse stops hovering over the thumbnail.
     *
     * Removes the classes for the actions container, and stops animating
     * the thumbnail contents.
     */
    _onHoverOut: function() {
        this.trigger('hoverOut');

        this._$actionsContainer
            .removeClass('left')
            .removeClass('right');

        this._stopAnimating();
    },

    /*
     * Stop animating this thumbnail.
     *
     * This is when moving the mouse outside of the thumbnail, or when the
     * caption editor is opened.
     */
    _stopAnimating: function() {
        if (this._scrollingThumbnail) {
            this._scrollingThumbnail = false;
            this.$('.file-thumbnail').children()
                .stop(true)
                .animate(
                    { 'margin-top': 0 },
                    { duration: 100 });
        }
    }
});
