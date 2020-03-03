(function() {


/**
 * Base class for displaying a comment in the review dialog.
 */
const BaseCommentView = Backbone.View.extend({
    tagName: 'li',

    thumbnailTemplate: null,

    events: {
        'click .delete-comment': '_deleteComment',
    },

    editorTemplate: _.template(dedent`
        <div class="edit-fields">
         <div class="edit-field">
          <div class="comment-text-field">
           <label class="comment-label" for="<%= id %>">
            <%- commentText %>
            <a href="#" role="button" class="delete-comment"
               aria-label="<%- deleteCommentText %>"
               title="<%- deleteCommentText %>"
               ><span class="fa fa-trash-o" aria-hidden="true"></span></a>
           </label>
           <pre id="<%= id %>" class="reviewtext rich-text"
                data-rich-text="true"><%- text %></pre>
          </div>
         </div>
         <div class="edit-field">
          <input class="issue-opened" id="<%= issueOpenedID %>"
                 type="checkbox">
          <label for="<%= issueOpenedID %>"><%- openAnIssueText %></label>
          <% if (showVerify) { %>
           <input class="issue-verify" id="<%= verifyIssueID %>"
                  type="checkbox">
           <label for="<%= verifyIssueID %>"><%- verifyIssueText %></label>
          <% } %>
         </div>
        </div>
    `),

    _DELETE_COMMENT_TEXT: gettext('Are you sure you want to delete this comment?'),

    /**
     * Initialize the view.
     */
    initialize() {
        this.$issueOpened = null;
        this.$editor = null;
        this.textEditor = null;
        this._origExtraData = _.clone(this.model.get('extraData'));

        this._hookViews = [];
    },

    /**
     * Remove the view.
     */
    remove() {
        this._hookViews.forEach(view => view.remove());
        this._hookViews = [];

        Backbone.View.prototype.remove.call(this);
    },

    /**
     * Return whether or not the comment needs to be saved.
     *
     * The comment will need to be saved if the inline editor is currently
     * open.
     *
     * Returns:
     *     boolean:
     *     Whether the comment needs to be saved.
     */
    needsSave() {
        return (this.inlineEditorView.isDirty() ||
                !_.isEqual(this.model.get('extraData'), this._origExtraData));
    },

    /**
     * Save the final state of the view.
     *
     * Saves the inline editor and notifies the caller when the model is
     * synced.
     *
     * Args:
     *     options (object):
     *         Options for the model save operation.
     */
    save(options) {
        /*
         * If the inline editor needs to be saved, ask it to do so. This will
         * call this.model.save(). If it does not, just save the model
         * directly.
         */
        if (this.inlineEditorView.isDirty()) {
            this.model.once('sync', () => options.success());
            this.inlineEditorView.submit();
        } else {
            this.model.save(_.extend({
                attrs: ['forceTextType', 'includeTextTypes', 'extraData'],
            }, options));
        }
    },

    /**
     * Render the comment view.
     *
     * Returns:
     *     BaseCommentView:
     *     This object, for chaining.
     */
    render() {
        this.$el
            .addClass('draft')
            .append(this.renderThumbnail())
            .append(this.editorTemplate({
                deleteCommentText: gettext('Delete comment'),
                commentText: gettext('Comment'),
                id: _.uniqueId('draft_comment_'),
                issueOpenedID: _.uniqueId('issue-opened'),
                openAnIssueText: gettext('Open an Issue'),
                text: this.model.get('text'),
                verifyIssueID: _.uniqueId('issue-verify'),
                showVerify: RB.EnabledFeatures.issueVerification,
                verifyIssueText: RB.CommentDialogView._verifyIssueText,
            }))
            .find('time.timesince')
                .timesince()
            .end();

        this.$issueOpened = this.$('.issue-opened')
            .prop('checked', this.model.get('issueOpened'))
            .change(() => {
                this.model.set('issueOpened',
                               this.$issueOpened.prop('checked'));

                if (!this.model.isNew()) {
                    /*
                     * We don't save the issueOpened attribute for unsaved
                     * models because the comment won't exist yet. If we did,
                     * clicking cancel when creating a new comment wouldn't
                     * delete the comment.
                     */
                    this.model.save({
                        attrs: ['forceTextType', 'includeTextTypes',
                                'issueOpened'],
                    });
                }
            });

        this._$issueVerify = this.$('.issue-verify')
            .prop('checked', this.model.requiresVerification())
            .change(() => {
                const extraData = _.clone(this.model.get('extraData'));
                extraData.require_verification =
                    this._$issueVerify.prop('checked');
                this.model.set('extraData', extraData);

                if (!this.model.isNew()) {
                    /*
                     * We don't save the extraData attribute for unsaved models
                     * because the comment won't exist yet. If we did, clicking
                     * cancel when creating a new comment wouldn't delete the
                     * comment.
                     */
                    this.model.save({
                        attrs: ['forceTextType', 'includeTextTypes',
                                'extra_data.require_verification'],
                    });
                }
            });

        const $editFields = this.$('.edit-fields');

        this.$editor = this.$('pre.reviewtext');

        this.inlineEditorView = new RB.RichTextInlineEditorView({
            el: this.$editor,
            editIconClass: 'rb-icon rb-icon-edit',
            notifyUnchangedCompletion: true,
            multiline: true,
            textEditorOptions: {
                bindRichText: {
                    model: this.model,
                    attrName: 'richText',
                },
            },
        });
        this.inlineEditorView.render();

        this.textEditor = this.inlineEditorView.textEditor;

        this.listenTo(this.inlineEditorView, 'complete', value => {
            const attrs = ['forceTextType', 'includeTextTypes',
                           'richText', 'text'];

            if (this.model.isNew()) {
                /*
                 * If this is a new comment, we have to send whether or not an
                 * issue was opened because toggling the issue opened checkbox
                 * before it is completed won't save the status to the server.
                 */
                attrs.push('extra_data.require_verification', 'issueOpened');
            }

            this.model.set({
                text: value,
                richText: this.textEditor.richText,
            });
            this.model.save({
                attrs: attrs,
            });
        });

        this.listenTo(this.model, `change:${this._getRawValueFieldsName()}`,
                      this._updateRawValue);
        this._updateRawValue();

        this.listenTo(this.model, 'saved', this.renderText);
        this.renderText();

        this.listenTo(this.model, 'destroying',
                      () => this.stopListening(this.model));

        RB.ReviewDialogCommentHook.each(hook => {
            const HookView = hook.get('viewType');
            const hookView = new HookView({
                extension: hook.get('extension'),
                model: this.model,
            });

            this._hookViews.push(hookView);

            $('<div class="edit-field"/>')
                .append(hookView.$el)
                .appendTo($editFields);
            hookView.render();
        });

        return this;
    },

    /**
     * Render the thumbnail for this comment.
     *
     * Returns:
     *     jQuery:
     *     The rendered thumbnail element.
     */
    renderThumbnail() {
        if (this.thumbnailTemplate === null) {
            return null;
        }

        return $(this.thumbnailTemplate(this.model.attributes));
    },

    /**
     * Render the text for this comment.
     */
    renderText() {
        const reviewRequest = this.model.get('parentObject').get('parentObject');

        if (this.$editor) {
            RB.formatText(this.$editor, {
                newText: this.model.get('text'),
                richText: this.model.get('richText'),
                isHTMLEncoded: true,
                bugTrackerURL: reviewRequest.get('bugTrackerURL'),
            });
        }
    },

    /**
     * Delete the comment associated with the model.
     */
    _deleteComment() {
        if (confirm(this._DELETE_COMMENT_TEXT)) {
            this.model.destroy();
        }
    },

    /**
     * Update the stored raw value of the comment text.
     *
     * This updates the raw value stored in the inline editor as a result of a
     * change to the value in the model.
     */
    _updateRawValue() {
        if (this.$editor) {
            this.inlineEditorView.options.hasRawValue = true;
            this.inlineEditorView.options.rawValue =
                this.model.get(this._getRawValueFieldsName()).text;
        }
    },

    /**
     * Return the field name for the raw value.
     *
     * Returns:
     *     string:
     *     The field name to use, based on the whether the user wants to use
     *     Markdown or not.
     */
    _getRawValueFieldsName() {
        return RB.UserSession.instance.get('defaultUseRichText')
               ? 'markdownTextFields'
               : 'rawTextFields';
    },
});


/**
 * Displays a view for diff comments.
 */
const DiffCommentView = BaseCommentView.extend({
    thumbnailTemplate: _.template(dedent`
        <div class="review-dialog-comment-diff"
             id="review_draft_comment_container_<%= id %>">
         <table class="sidebyside loading">
          <thead>
           <tr>
            <th class="filename"><%- revisionText %></th>
           </tr>
          </thead>
          <tbody>
           <% for (var i = 0; i < numLines; i++) { %>
            <tr><td><pre>&nbsp;</pre></td></tr>
           <% } %>
          </tbody>
         </table>
        </div>
    `),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     diffQueue (RB.DiffFragmentQueueView):
     *         The view that handles loading diff fragments.
     */
    initialize(options) {
        this.options = options;
        BaseCommentView.prototype.initialize.call(this, options);
    },

    /**
     * Render the comment view.
     *
     * After rendering, this will queue up a load of the diff fragment
     * to display. The view will show a spinner until the fragment has
     * loaded.
     *
     * Returns:
     *     DiffCommentView:
     *     This object, for chaining.
     */
    render() {
        BaseCommentView.prototype.render.call(this);

        const fileDiffID = this.model.get('fileDiffID');
        const interFileDiffID = this.model.get('interFileDiffID');

        this.options.diffQueue.queueLoad(
            this.model.id,
            interFileDiffID ? fileDiffID + '-' + interFileDiffID
                            : fileDiffID);

        return this;
    },

    /**
     * Render the thumbnail.
     *
     * Returns:
     *     jQuery:
     *     The rendered thumbnail element.
     */
    renderThumbnail() {
        const fileDiff = this.model.get('fileDiff');
        const interFileDiff = this.model.get('interFileDiff');
        let revisionText;

        if (interFileDiff) {
            revisionText = interpolate(
                gettext('%(filename)s (Diff revisions %(fileDiffRevision)s - %(interFileDiffRevision)s)'),
                {
                    filename: fileDiff.get('destFilename'),
                    fileDiffRevision: fileDiff.get('sourceRevision'),
                    inteFfileDiffRevision: interFileDiff.get('sourceRevision'),
                },
                true);
        } else {
            revisionText = interpolate(
                gettext('%(filename)s (Diff revision %(fileDiffRevision)s)'),
                {
                    filename: fileDiff.get('destFilename'),
                    fileDiffRevision: fileDiff.get('sourceRevision'),
                },
                true);
        }

        return $(this.thumbnailTemplate({
            id: this.model.get('id'),
            numLines: this.model.getNumLines(),
            revisionText: revisionText,
        }));
    },
});


/**
 * Displays a view for file attachment comments.
 */
const FileAttachmentCommentView = BaseCommentView.extend({
    thumbnailTemplate: _.template(dedent`
        <div class="file-attachment">
         <span class="filename">
          <a href="<%- reviewURL %>"><%- linkText %></a>
         </span>
         <span class="diffrevision"><%- revisionsStr %></span>
         <div class="thumbnail"><%= thumbnailHTML %></div>
        </div>
    `),

    /**
     * Render the thumbnail.
     *
     * Returns:
     *     jQuery:
     *     The rendered thumbnail element.
     */
    renderThumbnail() {
        const fileAttachment = this.model.get('fileAttachment');
        const diffAgainstFileAttachment =
            this.model.get('diffAgainstFileAttachment');
        const revision = fileAttachment.get('revision');
        let revisionsStr;

        if (!revision) {
            /* This predates having a revision. Don't show anything. */
            revisionsStr = '';
        } else if (diffAgainstFileAttachment) {
            revisionsStr = interpolate(
                gettext('(Revisions %(revision1)s - %(revision2)s)'),
                {
                    revision1: diffAgainstFileAttachment.get('revision'),
                    revision2: revision
                },
                true);
        } else {
            revisionsStr = interpolate(gettext('(Revision %s)'), [revision]);
        }

        return $(this.thumbnailTemplate(_.defaults({
            revisionsStr: revisionsStr
        }, this.model.attributes)));
    },
});


/**
 * Displays a view for general comments.
 */
const GeneralCommentView = BaseCommentView.extend({
    thumbnailTemplate: null,
});


/**
 * Displays a view for screenshot comments.
 */
const ScreenshotCommentView = BaseCommentView.extend({
    thumbnailTemplate: _.template(dedent`
        <div class="screenshot">
         <span class="filename">
          <a href="<%- screenshot.reviewURL %>"><%- displayName %></a>
         </span>
         <img src="<%= thumbnailURL %>" width="<%= width %>"
              height="<%= height %>" alt="<%- displayName %>" />
        </div>
    `),

    /**
     * Render the thumbnail.
     *
     * Returns:
     *     jQuery:
     *     The rendered thumbnail element.
     */
    renderThumbnail() {
        const screenshot = this.model.get('screenshot');

        return $(this.thumbnailTemplate(_.defaults({
            screenshot: screenshot.attributes,
            displayName: screenshot.getDisplayName()
        }, this.model.attributes)));
    },
});


/**
 * The header or footer for a review.
 */
const HeaderFooterCommentView = Backbone.View.extend({
    tagName: 'li',

    editorTemplate: _.template(dedent`
        <div class="edit-fields">
         <div class="edit-field">
          <div class="add-link-container">
           <a href="#" class="add-link"><%- linkText %></a>
          </div>
          <div class="comment-text-field">
           <label for="<%= id %>" class="comment-label">
            <%- commentText %>
           </label>
           <pre id="<%= id %>" class="reviewtext rich-text"
                data-rich-text="true"><%- text %></pre>
          </div>
         </div>
        </div>
    `),

    events: {
        'click .add-link': 'openEditor',
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     propertyName (string):
     *         The property name to modify (either ``bodyTop`` or
     *         ``bodyBottom`)).
     *
     *     richTextPropertyName (string):
     *         The property name of the rich text field corresponding to the
     *         ``propertyName``.
     *
     *     linkText (string):
     *         The text to show in the "add" link.
     *
     *     commentText (string):
     *         The text to show in the label for the comment field.
     */
    initialize(options) {
        this.propertyName = options.propertyName;
        this.richTextPropertyName = options.richTextPropertyName;
        this.linkText = options.linkText;
        this.commentText = options.commentText;

        this.$editor = null;
        this.textEditor = null;
    },

    /**
     * Set the text of the link.
     *
     * Args:
     *     linkText (string):
     *         The text to show in the "add" link.
     */
    setLinkText(linkText) {
        this.$('.add-link').text(linkText);
    },

    /**
     * Render the view.
     *
     * Returns:
     *     HeaderFooterCommentView:
     *     This object, for chaining.
     */
    render() {
        const text = this.model.get(this.propertyName);

        this.$el
            .addClass('draft')
            .append(this.editorTemplate({
                commentText: this.commentText,
                id: this.propertyName,
                linkText: this.linkText,
                text: text || '',
            }))
            .find('time.timesince')
                .timesince()
            .end();


        this.$editor = this.$('pre.reviewtext');

        this.inlineEditorView = new RB.RichTextInlineEditorView({
            el: this.$editor,
            editIconClass: 'rb-icon rb-icon-edit',
            notifyUnchangedCompletion: true,
            multiline: true,
            textEditorOptions: {
                bindRichText: {
                    model: this.model,
                    attrName: this.richTextPropertyName,
                },
            },
        });
        this.inlineEditorView.render();

        this.textEditor = this.inlineEditorView.textEditor;

        this.listenTo(this.inlineEditorView, 'complete', value => {
            this.model.set(this.propertyName, value);
            this.model.set(this.richTextPropertyName,
                           this.textEditor.richText);
            this.model.save({
                attrs: [this.propertyName, this.richTextPropertyName,
                        'forceTextType', 'includeTextTypes'],
            });
        });
        this.listenTo(this.inlineEditorView, 'cancel', () => {
            if (!this.model.get(this.propertyName)) {
                this._$editorContainer.hide();
                this._$linkContainer.show();
            }
        });

        this._$editorContainer = this.$('.comment-text-field');
        this._$linkContainer = this.$('.add-link-container');

        this.listenTo(this.model, `change:${this._getRawValueFieldsName()}`,
                      this._updateRawValue);
        this._updateRawValue();

        this.listenTo(this.model, 'saved', this.renderText);
        this.renderText();
    },

    /**
     * Render the text for this comment.
     */
    renderText() {
        if (this.$editor) {
            const text = this.model.get(this.propertyName);

            if (text) {
                const reviewRequest = this.model.get('parentObject');

                this._$editorContainer.show();
                this._$linkContainer.hide();
                RB.formatText(this.$editor, {
                    newText: text,
                    richText: this.model.get(this.richTextPropertyName),
                    isHTMLEncoded: true,
                    bugTrackerURL: reviewRequest.get('bugTrackerURL')
                });
            } else {
                this._$editorContainer.hide();
                this._$linkContainer.show();
            }
        }
    },

    /**
     * Return whether or not the comment needs to be saved.
     *
     * The comment will need to be saved if the inline editor is currently
     * open.
     *
     * Returns:
     *     boolean:
     *     Whether the comment needs to be saved.
     */
    needsSave() {
        return this.inlineEditorView.isDirty();
    },

    /**
     * Save the final state of the view.
     *
     * Args:
     *     options (object):
     *         Options for the model save operation.
     */
    save(options) {
        this.model.once('sync', () => options.success());
        this.inlineEditorView.submit();
    },

    /**
     * Open the editor.
     *
     * This is used for the 'Add ...' link handler, as well as for the default
     * state of the dialog when there are no comments.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the action.
     *
     * Returns:
     *     boolean:
     *     false, always.
     */
    openEditor(ev) {
        this._$linkContainer.hide();
        this._$editorContainer.show();

        this.inlineEditorView.startEdit();

        if (ev) {
            ev.preventDefault();
        }

        return false;
    },

    /**
     * Delete the comment.
     *
     * This is a no-op, since headers and footers can't be deleted.
     */
    _deleteComment() {
    },

    /**
     * Update the stored raw value of the comment text.
     *
     * This updates the raw value stored in the inline editor as a result of a
     * change to the value in the model.
     */
    _updateRawValue() {
        if (this.$editor) {
            const rawValues = this.model.get(this._getRawValueFieldsName());

            this.inlineEditorView.options.hasRawValue = true;
            this.inlineEditorView.options.rawValue =
                rawValues[this.propertyName];
        }
    },

    /**
     * Return the field name for the raw value.
     *
     * Returns:
     *     string:
     *     The field name to use, based on the whether the user wants to use
     *     Markdown or not.
     */
    _getRawValueFieldsName() {
        return RB.UserSession.instance.get('defaultUseRichText')
               ? 'markdownTextFields'
               : 'rawTextFields';
    },
});


/**
 * Creates a dialog for modifying a draft review.
 *
 * This provides editing capabilities for creating or modifying a new
 * review. The list of comments are retrieved from the server, providing
 * context for the comments.
 */
RB.ReviewDialogView = Backbone.View.extend({
    id: 'review-form-comments',
    className: 'review',

    template: _.template(dedent`
        <div class="edit-field">
         <input id="id_shipit" type="checkbox" />
         <label for="id_shipit"><%- shipItText %></label>
        </div>
        <div class="review-dialog-hooks-container"></div>
        <div class="edit-field body-top"></div>
        <ol id="review-dialog-body-top-comments" class="review-comments"></ol>
        <ol id="review-dialog-general-comments" class="review-comments"></ol>
        <ol id="review-dialog-screenshot-comments" class="review-comments"></ol>
        <ol id="review-dialog-file-attachment-comments" class="review-comments"></ol>
        <ol id="review-dialog-diff-comments" class="review-comments"></ol>
        <ol id="review-dialog-body-bottom-comments" class="review-comments"></ol>
        <div class="spinner"><span class="fa fa-spinner fa-pulse"></span></div>
        <div class="edit-field body-bottom"></div>
    `),

    /**
     * Initialize the review dialog.
     *
     * Args:
     *     container (string, optional):
     *         The selector for a container element for the review dialog.
     *
     *     options (object):
     *         Options for the view.
     *
     *     reviewRequestEditor (RB.ReviewRequestEditor):
     *         The review request editor.
     */
    initialize(options) {
        this.options = options;
        this._$diffComments = $();
        this._$fileAttachmentComments = $();
        this._$generalComments = $();
        this._$screenshotComments = $();
        this._$dlg = null;
        this._$buttons = null;
        this._$spinner = null;
        this._$shipIt = null;

        this._commentViews = [];
        this._hookViews = [];

        _.bindAll(this, '_onAddCommentClicked');

        const reviewRequest = this.model.get('parentObject');
        this._diffQueue = new RB.DiffFragmentQueueView({
            containerPrefix: 'review_draft_comment_container',
            reviewRequestPath: reviewRequest.get('reviewURL'),
            queueName: 'review_draft_diff_comments',
        });

        this._diffCommentsCollection = new RB.ResourceCollection([], {
            model: RB.DiffComment,
            parentResource: this.model,
            extraQueryData: {
                'order-by': 'filediff,first_line',
            },
        });

        this._bodyTopView = new HeaderFooterCommentView({
            model: this.model,
            propertyName: 'bodyTop',
            richTextPropertyName: 'bodyTopRichText',
            linkText: gettext('Add header'),
            commentText: gettext('Header'),
        });

        this._bodyBottomView = new HeaderFooterCommentView({
            model: this.model,
            propertyName: 'bodyBottom',
            richTextPropertyName: 'bodyBottomRichText',
            linkText: gettext('Add footer'),
            commentText: gettext('Footer'),
        });

        this.listenTo(this._diffCommentsCollection, 'add', comment => {
            const view = new DiffCommentView({
                model: comment,
                diffQueue: this._diffQueue,
            });
            this._renderComment(view, this._$diffComments);
        });

        this._fileAttachmentCommentsCollection = new RB.ResourceCollection([], {
            model: RB.FileAttachmentComment,
            parentResource: this.model,
        });

        this.listenTo(this._fileAttachmentCommentsCollection, 'add',
                      comment => {
            const view = new FileAttachmentCommentView({ model: comment });
            this._renderComment(view, this._$fileAttachmentComments);
        });

        this._$lastGeneralComment = null;

        this._generalCommentsCollection = new RB.ResourceCollection([], {
            model: RB.GeneralComment,
            parentResource: this.model,
        });

        this.listenTo(this._generalCommentsCollection, 'add', comment => {
            const view = new GeneralCommentView({ model: comment });
            this._renderComment(view, this._$generalComments);
        });

        this._screenshotCommentsCollection = new RB.ResourceCollection([], {
            model: RB.ScreenshotComment,
            parentResource: this.model,
        });

        this.listenTo(this._screenshotCommentsCollection, 'add', comment => {
            const view = new ScreenshotCommentView({ model: comment });
            this._renderComment(view, this._$screenshotComments);
        });

        this._defaultUseRichText =
            RB.UserSession.instance.get('defaultUseRichText');

        this._queryData = {
            'force-text-type': 'html'
        };

        if (this._defaultUseRichText) {
            this._queryData['include-text-types'] = 'raw,markdown';
        } else {
            this._queryData['include-text-types'] = 'raw';
        }

        this._setTextTypeAttributes(this.model);

        this.options.reviewRequestEditor.incr('editCount');
    },

    /**
     * Remove the dialog from the DOM.
     *
     * This will remove all the extension hook views from the dialog,
     * and then remove the dialog itself.
     */
    remove() {
        if (this._publishButton) {
            this._publishButton.remove();
            this._publishButton = null;
        }

        this._hookViews.forEach(view => view.remove());
        this._hookViews = [];

        _super(this).remove.call(this);
    },

    /**
     * Close the review dialog.
     *
     * The dialog will be removed from the screen, and the "closed"
     * event will be triggered.
     */
    close() {
        this.options.reviewRequestEditor.decr('editCount');
        this._$dlg.modalBox('destroy');
        this.trigger('closed');

        this.remove();
    },

    /**
     * Render the dialog.
     *
     * The dialog will be shown on the screen, and the comments from
     * the server will begin loading and rendering.
     *
     * Returns:
     *     RB.ReviewDialogView:
     *     This object, for chaining.
     */
    render() {
        this.$el.html(this.template({
            addHeaderText: gettext('Add header'),
            addFooterText: gettext('Add footer'),
            shipItText: gettext('Ship It'),
            markdownDocsURL: MANUAL_URL + 'users/markdown/',
            markdownText: gettext('Markdown Reference'),
        }));

        this._$diffComments = this.$('#review-dialog-diff-comments');
        this._$fileAttachmentComments =
            this.$('#review-dialog-file-attachment-comments');
        this._$generalComments = this.$('#review-dialog-general-comments');
        this._$screenshotComments =
            this.$('#review-dialog-screenshot-comments');
        this._$spinner = this.$('.spinner');
        this._$shipIt = this.$('#id_shipit');

        const $hooksContainer = this.$('.review-dialog-hooks-container');

        RB.ReviewDialogHook.each(hook => {
            const HookView = hook.get('viewType');
            const hookView = new HookView({
                extension: hook.get('extension'),
                model: this.model,
            });

            this._hookViews.push(hookView);

            $hooksContainer.append(hookView.$el);
            hookView.render();
        });

        this._bodyTopView.$el.appendTo(
            this.$('#review-dialog-body-top-comments'));
        this._bodyBottomView.$el.appendTo(
            this.$('#review-dialog-body-bottom-comments'));

        /*
         * Even if the model is already loaded, we may not have the right text
         * type data. Force it to reload.
         */
        this.model.set('loaded', false);

        this.model.ready({
            data: this._queryData,
            ready: () => {
                this._renderDialog();
                this._bodyTopView.render();
                this._bodyBottomView.render();

                if (this.model.isNew() || this.model.get('bodyTop') === '') {
                    this._bodyTopView.openEditor();
                }

                if (this.model.isNew()) {
                    this._$spinner.remove();
                    this._$spinner = null;

                    this._handleEmptyReview();
                } else {
                    this._$shipIt.prop('checked', this.model.get('shipIt'));
                    this._loadComments();
                }

                this.listenTo(this.model, 'change:bodyBottom',
                              this._handleEmptyReview);
            }
        });

        return this;
    },

    /**
     * Load the comments from the server.
     *
     * This will begin chaining together the loads of each set of
     * comment types. Each loaded comment will be rendered to the
     * dialog once loaded.
     */
    _loadComments() {
        const collections = [
            this._screenshotCommentsCollection,
            this._fileAttachmentCommentsCollection,
            this._diffCommentsCollection
        ];

        if (RB.EnabledFeatures.generalComments) {
            /*
             * Prepend the General Comments so they're fetched and shown
             * first.
             */
            collections.unshift(this._generalCommentsCollection);
        }

        this._loadCommentsFromCollection(collections, () => {
            this._$spinner.remove();
            this._$spinner = null;

            this._handleEmptyReview();
        });
    },

    /**
     * Properly set the view when the review is empty.
     */
    _handleEmptyReview() {
        /*
         * We only display the bottom textarea if we have comments or the user
         * has previously set the bottom textarea -- we don't want the user to
         * not be able to remove their text.
         */
        if (this._commentViews.length === 0 && !this.model.get('bodyBottom')) {
            this._bodyBottomView.$el.hide();
            this._bodyTopView.setLinkText(gettext('Add text'));
        }
    },

    /**
     * Load the comments from a collection.
     *
     * This is part of the load comments flow. The list of remaining
     * collections are passed, and the first one will be removed
     * from the list and loaded.
     *
     * Args:
     *     collections (array):
     *         The list of collections left to load.
     *
     *     onDone (function):
     *         The function to call when all collections have been loaded.
     */
    _loadCommentsFromCollection(collections, onDone) {
        const collection = collections.shift();

        if (collection) {
            collection.fetchAll({
                data: this._queryData,
                success: () => {
                    if (collection === this._diffCommentsCollection) {
                        this._diffQueue.loadFragments();
                    }

                    this._loadCommentsFromCollection(collections, onDone);
                },
                error: rsp => {
                    // TODO: Provide better error output.
                    alert(rsp.errorText);
                }
            });
        } else {
            onDone();
        }
    },

    /**
     * Render a comment to the dialog.
     *
     * Args:
     *     view (BaseCommentView):
     *         The view to render.
     *
     *     $container (jQuery):
     *         The container to add the view to.
     */
    _renderComment(view, $container) {
        this._setTextTypeAttributes(view.model);

        this._commentViews.push(view);

        this.listenTo(view.model, 'destroyed', () => {
            view.$el.fadeOut({
                complete: () => {
                    view.remove();
                    this._handleEmptyReview();
                },
            });

            this._commentViews = _.without(this._commentViews, view);
        });

        $container.append(view.$el);
        view.render();

        this._$dlg.scrollTop(view.$el.position().top +
                             this._$dlg.getExtents('p', 't'));
    },

    /**
     * Render the dialog.
     *
     * This will create and render a dialog to the screen, adding
     * this view's element as the child.
     */
    _renderDialog() {
        const $leftButtons = $('<div class="review-dialog-buttons-left"/>');
        const $rightButtons = $('<div class="review-dialog-buttons-right"/>');
        const buttons = [$leftButtons, $rightButtons];

        if (RB.EnabledFeatures.generalComments) {
            $leftButtons.append(
                $('<input type="button" />')
                    .val(gettext('Add General Comment'))
                    .attr('title',
                          gettext('Add a new general comment to the review'))
                    .click(this._onAddCommentClicked)
            );
        }

        $rightButtons.append(
            $('<div id="review-form-publish-split-btn-container" />'));

        $rightButtons.append(
            $('<input type="button"/>')
                .val(gettext('Discard Review'))
                .click(() => this._onDiscardClicked()));

        $rightButtons.append(
            $('<input type="button"/>')
                .val(gettext('Close'))
                .click(() => {
                    this._saveReview(false);
                    return false;
                }));

        const reviewRequest = this.model.get('parentObject');

        this._$dlg = $('<div/>')
            .attr('id', 'review-form')
            .append(this.$el)
            .modalBox({
                container: this.options.container || 'body',
                boxID: 'review-form-modalbox',
                title: interpolate(
                    gettext('Review for: %s'),
                    [reviewRequest.get('summary')]),
                stretchX: true,
                stretchY: true,
                buttons: buttons,
            })
            .keypress(e => e.stopPropagation())
            .attr('scrollTop', 0)
            .trigger('ready');

        /* Must be done after the dialog is rendered. */

        this._publishButton = new RB.SplitButtonView({
            el: $('#review-form-publish-split-btn-container'),
            text: gettext('Publish Review'),
            ariaMenuLabel: gettext('More publishing options'),
            click: () => {
                this._saveReview(true);
                return false;
            },
            direction: 'up',
            alternatives: [
                {
                    text: gettext('... and only e-mail the owner'),
                    click: () => {
                        this._saveReview(true, {
                            publishToOwnerOnly: true
                        });
                        this.close();
                        return false;
                    },
                },
                {
                    text: gettext('... and archive the review request'),
                    click: () => {
                        this._saveReview(true, {
                            publishAndArchive: true,
                        });
                        this.close();
                        return false;
                    },
                }
            ],
        });

        this._publishButton.render();

        this._$buttons = this._$dlg.modalBox('buttons');
    },

    /**
     * Handle a click on the "Add Comment" button.
     *
     * Returns:
     *     boolean:
     *     This always returns false to indicate that the dialog should not
     *     close.
     */
    _onAddCommentClicked() {
        const comment = this.model.createGeneralComment(
            undefined,
            RB.UserSession.instance.get('commentsOpenAnIssue'));

        this._generalCommentsCollection.add(comment);
        this._bodyBottomView.$el.show();
        this._commentViews[this._commentViews.length - 1]
            .inlineEditorView.startEdit();

        return false;
    },

    /**
     * Handle a click on the "Discard Review" button.
     *
     * Prompts the user to confirm that they want the review discarded.
     * If they confirm, the review will be discarded.
     *
     * Returns:
     *     boolean:
     *     This always returns false to indicate that the dialog should not
     *     close.
     */
    _onDiscardClicked() {
        const $cancelButton = $('<input type="button">')
            .val(gettext('Cancel'));

        const $discardButton = $('<input type="button">')
            .val(gettext('Discard'))
            .click(() => {
                this.close();
                this.model.destroy({
                    success: () => RB.DraftReviewBannerView.instance
                        .hideAndReload(),
                });
            });

        $('<p/>')
            .text(gettext('If you discard this review, all related comments will be permanently deleted.'))
            .modalBox({
                title: gettext('Are you sure you want to discard this review?'),
                buttons: [
                    $cancelButton,
                    $discardButton,
                ],
            });

        return false;
    },

    /**
     * Save the review.
     *
     * First, this loops over all the comment editors and saves any which are
     * still in the editing phase.
     *
     * Args:
     *     publish (boolean):
     *         Whether the review should be published.
     *
     *     options (object):
     *         Options for the model save operation.
     */
    _saveReview(publish, options={}) {
        if (publish && options.publishToOwnerOnly) {
            this.model.set('publishToOwnerOnly', true);
        }

        if (publish && options.publishAndArchive) {
            this.model.set('publishAndArchive', true);
        }

        this._$buttons.prop('disabled');

        let madeChanges = false;
        $.funcQueue('reviewForm').clear();

        function maybeSave(view) {
            if (view.needsSave()) {
                $.funcQueue('reviewForm').add(() => {
                    madeChanges = true;
                    view.save({
                        success: () => $.funcQueue('reviewForm').next(),
                    });
                });
            }
        }

        maybeSave(this._bodyTopView);
        maybeSave(this._bodyBottomView);
        this._commentViews.forEach(view => maybeSave(view));

        $.funcQueue('reviewForm').add(() => {
            const shipIt = this._$shipIt.prop('checked');
            const saveFunc = publish ? this.model.publish : this.model.save;

            if (this.model.get('public') === publish &&
                this.model.get('shipIt') === shipIt) {
                $.funcQueue('reviewForm').next();
            } else {
                madeChanges = true;
                this.model.set({
                    shipIt: shipIt,
                });

                saveFunc.call(this.model, {
                    attrs: [
                        'forceTextType',
                        'includeTextTypes',
                        'public',
                        'publishAndArchive',
                        'publishToOwnerOnly',
                        'shipIt',
                    ],
                    success: () => $.funcQueue('reviewForm').next(),
                    error: function() {
                        console.error('Failed to save review', arguments);
                    },
                });
            }
        });

        $.funcQueue('reviewForm').add(() => {
            const reviewBanner = RB.DraftReviewBannerView.instance;

            this.close();

            if (reviewBanner) {
                if (publish) {
                    reviewBanner.hideAndReload();
                } else if (this.model.isNew() && !madeChanges) {
                    reviewBanner.hide();
                } else {
                    reviewBanner.show();
                }
            }
        });

        $.funcQueue('reviewForm').start();
    },

    /**
     * Set the text attributes on a model for forcing and including types.
     *
     * Args:
     *     model (Backbone.Model):
     *         The model to set the text type attributes on.
     */
    _setTextTypeAttributes(model) {
        model.set({
            forceTextType: 'html',
            includeTextTypes: this._defaultUseRichText
                              ? 'raw,markdown' : 'raw'
        });
    },
}, {
    /*
     * Add some useful singletons to ReviewDialogView for managing the
     * review dialog.
     */

    _instance: null,

    /**
     * Create a ReviewDialogView.
     *
     * Only one is allowed on the screen at any given time.
     *
     * Args:
     *     options (object):
     *         Options for the dialog.
     *
     * Option Args:
     *     container (jQuery):
     *         The DOM container to attach the dialog to.
     *
     *     review (RB.Review):
     *         The review to show in this dialog.
     *
     *     reviewRequestEditor (RB.ReviewRequestEditor):
     *         The review request editor model.
     */
    create(options={}) {
        console.assert(!RB.ReviewDialogView._instance,
                       'A ReviewDialogView is already opened');
        console.assert(options.review, 'A review must be specified');

        const dialog = new RB.ReviewDialogView({
            container: options.container,
            model: options.review,
            reviewRequestEditor: options.reviewRequestEditor,
        });
        RB.ReviewDialogView._instance = dialog;

        dialog.render();

        dialog.on('closed', () => {
            RB.ReviewDialogView._instance = null;
        });

        return dialog;
    },
});


})();
