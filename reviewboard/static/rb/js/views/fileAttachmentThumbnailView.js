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
        'click .delete': '_onDeleteClicked',
        'click .file-add-comment a': '_onAddCommentClicked'
    },

    template: _.template([
        '<div class="file">',
        ' <ul class="actions" />',
        ' <div class="file-header">',
        '  <a class="download">',
        '   <img class="icon" />',
        '   <span class="filename"><%- filename %></span>',
        '  </a>',
        ' </div>',
        ' <div class="file-thumbnail-container" />',
        ' <div class="file-caption-container">',
        '  <div class="file-caption can-edit">', /* spaceless */
        '<a href="<%- downloadURL %>"',
        '   class="edit <% if (!caption) { %>empty-caption<% } %>">',
        '<% if (caption) { %><%- caption %><% } else { %><%- noCaptionText %><% } %>',
        '</a>',
        '</div>', /* endspaceless */
        ' </div>',
        '</div>'
    ].join('')),

    actionsTemplate: _.template([
        '<% if (loaded) { %>',
        '<%   if (reviewURL) { %>',
        ' <li class="file-review"><a href="<%- reviewURL %>"><%- reviewText %></a></li>',
        '<%   } else { %>',
        ' <li class="file-add-comment"><a href="#"><%- addCommentText %></a></li>',
        '<%   } %>',
        ' <li class="delete">',
        '  <a href="#" alt="<%- deleteFileText %>"',
        '     title="<%- deleteFileText %>">',
        '   <span class="ui-icon ui-icon-trash"></span>',
        '  </a>',
        ' </li>',
        '<% } %>'
    ].join('')),

    thumbnailContainerTemplate: _.template([
        '<% if (!loaded) { %>',
        ' <img class="file-thumbnail spinner" width="16" height="16" ',
              'src="<%- spinnerURL %>" />',
        '<% } else { %>',
        '<%   if (reviewURL) { %>',
        ' <a href="<%- reviewURL %>" class="file-thumbnail-overlay"',
        '    alt="<%- reviewAltText %>" title="<%- reviewAltText %>"> </a>',
        '<%   } %>',
        '<%=  thumbnailHTML %>',
        '<% } %>'
    ].join('')),

    initialize: function(options) {
        this.options = options;

        this._draftComment = null;
        this._comments = [];
        this._commentsProcessed = false;
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
        this._$addCommentButton = this.$('.file-add-comment a');

        this.listenTo(this.model, 'destroy', function() {
            this.$el.fadeOut(function() {
                self.remove();
            });
        });

        this.listenTo(this.model, 'change:caption', this._onCaptionChanged);
        this._onCaptionChanged();

        if (this.options.renderThumbnail) {
            this._$actions = this.$('.actions');
            this._$fileHeader = this.$('.file-header');
            this._$captionContainer = this.$('.file-caption-container');
            this._$thumbnailContainer = this.$('.file-thumbnail-container');

            this._$fileHeader.find('.download')
                .bindProperty('href', this.model, 'downloadURL', {
                    elementToModel: false
                });

            this._$fileHeader.find('.icon')
                .bindProperty('src', this.model, 'iconURL', {
                    elementToModel: false
                });

            this._$fileHeader.find('.filename')
                .bindProperty('text', this.model, 'filename', {
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
                    el: this._$addCommentButton,
                    side: 'b',
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
        this.$el
            .html(this.template(_.defaults({
                noCaptionText: gettext('No caption')
            }, this.model.attributes)))
            .addClass(this.className);
    },

    /*
     * Renders the thumbnail for the file attachment.
     */
    _renderThumbnail: function() {
        this._$thumbnailContainer.html(
            this.thumbnailContainerTemplate(_.extend({
                reviewAltText: gettext('Click to review'),
                spinnerURL: STATIC_URLS['rb/images/spinner.gif']
            }, this.model.attributes)));
    },

    /*
     * Handler for when the model's 'loaded' property changes.
     *
     * Depending on if the file attachment is now loaded, either a
     * blank spinner thumbnail will be shown, or a full thumbnail.
     */
    _onLoadedChanged: function() {
        var $fileHeaderChildren = this._$fileHeader.children();

        if (this.model.get('loaded')) {
            $fileHeaderChildren.show();
            this._$actions.show();
            this._$captionContainer.css('visibility', 'visible');
        } else {
            $fileHeaderChildren.hide();
            this._$actions.hide();
            this._$captionContainer.css('visibility', 'hidden');
        }

        this._$actions.html(this.actionsTemplate(_.defaults({
            deleteFileText: gettext('Delete this file'),
            reviewText: gettext('Review'),
            addCommentText: gettext('New Comment')
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
     * Handler for the Delete button.
     *
     * Deletes the file attachment from the review request draft.
     */
    _onDeleteClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this.model.destroy();
    }
});
