/**
 * Handles editing a reply to a comment in a review.
 *
 * This will handle the "New Comment" link and the draft banners for the
 * review.
 */
RB.ReviewRequestPage.ReviewReplyEditorView = Backbone.View.extend({
    commentTemplate: _.template(dedent`
        <li <% if (isDraft) { %>class="draft"<% } %>
            <% if (commentID) { %>data-comment-id="<%= commentID %>"<% } %>>
         <% if (anchorName) { %>
          <a class="comment-anchor" name="<%- anchorName %>"></a>
          <div class="floating-anchor">
           <a href="#<%- anchorName %>"
              class="fa fa-link fa-flip-horizontal"></a>
          </div>
         <% } %>
         <div class="comment-author">
          <label for="<%= id %>">
           <div class="avatar-container"><%= avatarHTML %></div>
           <div class="user-reply-info">
            <a href="<%= userPageURL %>" class="user"><%- fullName %></a>
        <% if (timestamp) { %>
            <span class="timestamp">
             <time class="timesince" datetime="<%= timestampISO %>">
        <%= timestamp %></time>
            </span>
        <% } %>
           </div>
          </label>
         </div>
         <div>
          <pre id="<%= id %>" class="comment-text reviewtext"><%- text %></pre>
         </div>
        </li>
    `),

    events: {
        'click .add_comment_link': '_onAddCommentClicked',
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     reviewRequestEditor (RB.ReviewRequestEditor):
     *         The editor model.
     */
    initialize(options) {
        this.options = options;
        this._$addCommentLink = null;
        this._$draftComment = null;
        this._$editor = null;
        this._$commentsList = null;
        this._inlineEditorView = null;
    },

    /**
     * Render the comment section.
     *
     * If there were any draft comments found, then editors will be
     * created for them, the New Comment link will be hidden.
     *
     * Returns:
     *     RB.ReviewRequestPage.ReviewReplyEditorView:
     *     This object, for chaining.
     */
    render() {
        this._$addCommentLink = this.$('.add_comment_link');
        this._$commentsList = this.$('.reply-comments');

        /* See if there's a draft comment to import from the page. */
        const $draftComment = this._$commentsList.children('.draft');

        if ($draftComment.length !== 0) {
            const $time = $draftComment.find('time');
            const $reviewText = $draftComment.find('.reviewtext');

            this.model.set({
                commentID: $draftComment.data('comment-id'),
                text: $reviewText.html(),
                timestamp: new Date($time.attr('datetime')),
                richText: $reviewText.hasClass('rich-text'),
                hasDraft: true,
            });
            this._createCommentEditor($draftComment);
        }

        this.listenTo(this.model, 'textUpdated', () => {
            if (this._$editor) {
                const reviewRequest =
                    this.model.get('review').get('parentObject');

                RB.formatText(this._$editor, {
                    newText: this.model.get('text'),
                    richText: this.model.get('richText'),
                    bugTrackerURL: reviewRequest.get('bugTrackerURL'),
                });
            }
        });

        this.model.on('resetState', () => {
            if (this._$draftComment) {
                this._$draftComment.fadeOut(() => {
                    this._$draftComment.remove();
                    this._$draftComment = null;
                });
            }

            this._$addCommentLink.fadeIn();
        });

        this.model.on('published', this._onPublished, this);
    },

    /**
     * Open the comment editor for a new comment.
     */
    openCommentEditor() {
        this._createCommentEditor(this._makeCommentElement());
        this._inlineEditorView.startEdit();
    },

    /**
     * Return whether this editor needs to be saved.
     *
     * Returns:
     *     boolean:
     *     Whether the comment editor has unsaved content.
     */
    needsSave() {
        return this._inlineEditorView && this._inlineEditorView.isDirty();
    },

    /**
     * Save the editor.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the save is complete.
     */
    async save() {
        const value = this._inlineEditorView.submit({
            preventEvents: true,
        });

        if (value) {
            const reviewRequestEditor = this.options.reviewRequestEditor;

            if (reviewRequestEditor) {
                reviewRequestEditor.decr('editCount');
            }

            this.model.set({
                richText: this._inlineEditorView.textEditor.richText,
                text: value,
            });

            await this.model.save();
        }
    },

    /**
     * Create a comment editor for an element.
     *
     * Args:
     *     $draftComment (jQuery):
     *         The draft comment element.
     */
    _createCommentEditor($draftComment) {
        const reviewRequestEditor = this.options.reviewRequestEditor;

        this._$draftComment = $draftComment;

        this._$editor = $draftComment.find('pre.reviewtext');
        const inlineEditorView = new RB.RichTextInlineEditorView({
            editIconClass: 'rb-icon rb-icon-edit',
            el: this._$editor,
            formClass: 'inline-comment-editor',
            hasRawValue: true,
            multiline: true,
            notifyUnchangedCompletion: true,
            rawValue: this._$editor.data('raw-value') || '',
            textEditorOptions: {
                richText: this._$editor.hasClass('rich-text'),
            },
        });
        inlineEditorView.render();

        this.listenTo(inlineEditorView, 'beginEdit', () => {
            if (reviewRequestEditor) {
                reviewRequestEditor.incr('editCount');
            }
        });

        this.listenTo(inlineEditorView, 'complete', value => {
            if (reviewRequestEditor) {
                reviewRequestEditor.decr('editCount');
            }

            this.model.set({
                richText: inlineEditorView.textEditor.richText,
                text: value,
            });
            this.model.save();
        });

        this.listenTo(inlineEditorView, 'cancel', () => {
            if (reviewRequestEditor) {
                reviewRequestEditor.decr('editCount');
            }

            this.model.resetStateIfEmpty();
        });

        this._inlineEditorView = inlineEditorView;

        this._$editor.removeAttr('data-raw-value');

        this._$addCommentLink.hide();
    },

    /**
     * Create an element for the comment form.
     *
     * Args:
     *     options (object, optional):
     *         Options for the comment element.
     *
     * Option Args:
     *     now (Moment):
     *         The current time.
     *
     *     richText (boolean):
     *         Whether the text is in a rich-text format.
     *
     *     text (string):
     *         The text for the comment.
     *
     * Returns:
     *     jQuery:
     *     The newly-created element.
     */
    _makeCommentElement(options={}) {
        const userSession = RB.UserSession.instance;
        const reviewRequest = this.model.get('review').get('parentObject');

        const now = (
            options.now ||
            moment().utcOffset(userSession.get('timezoneOffset')));

        const $el = $(this.commentTemplate(_.extend({
                anchorName: null,
                id: _.uniqueId('draft_comment_'),
                text: '',
                commentID: null,
                userPageURL: userSession.get('userPageURL'),
                fullName: userSession.get('fullName'),
                avatarHTML: userSession.getAvatarHTML(32),
                isDraft: true,
                timestampISO: now.format(),

                /*
                 * Note that we format the a.m./p.m. this way to match
                 * what's coming from the Django templates.
                 */
                timestamp: now.format('MMMM Do, YYYY, h:mm ') +
                           (now.hour() < 12 ? 'a.m.' : 'p.m.'),
            }, options)))
            .find('.user')
                .user_infobox()
            .end()
            .find('time.timesince')
                .timesince()
            .end();

        Djblets.enableRetinaImages($el);

        if (options.text) {
            RB.formatText($el.find('.reviewtext'), {
                newText: options.text,
                richText: options.richText,
                bugTrackerURL: reviewRequest.get('bugTrackerURL'),
            });
        }

        $el.appendTo(this._$commentsList);

        return $el;
    },

    /**
     * Handler for when the New Comment link is clicked.
     *
     * Creates a new comment form and editor.
     *
     * Args:
     *     e (Event):
     *         The event that triggered the callback.
     */
    _onAddCommentClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this.openCommentEditor();
    },

    /**
     * Handler for when the reply is published.
     *
     * Updates the draft comment to be a standard comment, and brings back
     * the New Comment link.
     */
    _onPublished() {
        if (this._$draftComment) {
            const model = this.model;
            const contextType = model.get('contextType');

            this._$draftComment.replaceWith(this._makeCommentElement({
                anchorName: model.get('anchorPrefix') +
                            model.get('replyObject').id,
                commentID: model.get('commentID'),
                text: model.get('text'),
                richText: model.get('richText'),
                isDraft: false,
            }));

            this._$draftComment = null;
        }
    },
});
