(function() {


var BaseCommentView,
    DiffCommentView,
    FileAttachmentCommentView,
    ScreenshotCommentView;


/*
 * Base class for displaying a comment in the review dialog.
 */
BaseCommentView = Backbone.View.extend({
    tagName: 'li',

    thumbnailTemplate: '',

    editorTemplate: _.template([
        '<div class="edit-fields">',
        ' <div class="edit-field">',
        '  <div class="comment-text-field"></div>',
        ' </div>',
        ' <div class="edit-field">',
        '  <input class="issue-opened" id="<%= issueOpenedID %>" ',
        '         type="checkbox" />',
        '  <label for="<%= issueOpenedID %>"><%- openAnIssueText %></label>',
        ' </div>',
        ' <div class="edit-field">',
        '  <input class="enable-markdown" id="<%= enableMarkdownID %>" ',
        '         type="checkbox" />',
        '  <label for="<%= enableMarkdownID %>"><%- enableMarkdownText %>',
        '</label>',
        ' </div>',
        '</div>'
    ].join('')),

    initialize: function() {
        this.$issueOpened = null;
        this.textEditor = null;

        this._origIssueOpened = this.model.get('issueOpened');
        this._origRichText = this.model.get('richText');
        this._origExtraData = _.clone(this.model.get('extraData'));
        this._hookViews = [];

        this.model.set('includeTextTypes', 'raw');
    },

    remove: function() {
        _.each(this._hookViews, function(hookView) {
            hookView.remove();
        });

        this._hookViews = [];

        _super(this).remove.call(this);
    },

    /*
     * Returns whether or not the comment needs to be saved.
     *
     * The comment will need to be saved if the text field is dirty,
     * or if the issueOpened checkbox has changed.
     */
    needsSave: function() {
        var newValue = this.textEditor.getText(),
            newIssueOpened = this.$issueOpened.prop('checked');
            newRichText = this.textEditor.richText;

        return this.model.get('text') !== newValue ||
               this.model.get('issueOpened') !== newIssueOpened ||
               this.model.get('richText') !== newRichText ||
               !_.isEqual(this.model.get('extraData'), this._origExtraData);
    },

    /*
     * Saves the final state of the view.
     *
     * This will trigger a save of the editable, which will update the
     * comment. It will then invoke the provided callback.
     */
    save: function(options) {
        this.model.set({
            issueOpened: this.$issueOpened.prop('checked'),
            richText: this.textEditor.richText,
            text: this.textEditor.getText()
        });
        this.model.save(options);
    },

    /*
     * Renders the comment view.
     */
    render: function() {
        var $editFields;

        this.$el
            .append(this.renderThumbnail())
            .append($(this.editorTemplate({
                text: this.model.get('text'),
                issueOpenedID: _.uniqueId('issue-opened'),
                openAnIssueText: gettext('Open an Issue'),
                enableMarkdownID: _.uniqueId('enable-markdown'),
                enableMarkdownText: gettext('Enable Markdown')
            })));

        this.textEditor = new RB.TextEditorView({
            el: this.$('.comment-text-field'),
            text: this.model.get('text'),
            bindRichText: {
                model: this.model,
                attrName: 'richText'
            }
        });
        this.textEditor.render();
        this.textEditor.show();
        this.textEditor.bindRichTextCheckbox(this.$('.enable-markdown'));

        this.$issueOpened = this.$('.issue-opened')
            .prop('checked', this.model.get('issueOpened'));

        $editFields = this.$('.edit-fields');

        RB.ReviewDialogCommentHook.each(function(hook) {
            var HookView = hook.get('viewType'),
                hookView = new HookView({
                    model: this.model
                });

            this._hookViews.push(hookView);

            $editFields.append(
                $('<div class="edit-field"/>')
                    .append(hookView.$el));
            hookView.render();
        }, this);

        return this;
    },

    /*
     * Renders the thumbnail for this comment.
     */
    renderThumbnail: function() {
        return $(this.thumbnailTemplate(this.model.attributes));
    }
});


/*
 * Displays a view for diff comments.
 */
DiffCommentView = BaseCommentView.extend({
    thumbnailTemplate: _.template([
        '<div id="review_draft_comment_container_<%= id %>">',
        ' <table class="sidebyside loading">',
        '  <thead>',
        '   <tr>',
        '    <th class="filename">',
        '     <%- fileDiff.destFilename %>',
        '     <% if (interFileDiff) { %>',
        '      (Diff revisions <%- fileDiff.sourceRevision %> - ',
        '       <%- interFileDiff.sourceRevision %>)',
        '     <% } else { %>',
        '      (Diff revision <%- fileDiff.sourceRevision %>)',
        '     <% } %>',
        '    </th>',
        '   </tr>',
        '  </thead>',
        '  <tbody>',
        '   <% for (var i = 0; i < numLines; i++) { %>',
        '    <tr><td><pre>&nbsp;</pre></td></tr>',
        '   <% } %>',
        '  </tbody>',
        ' </table>',
        '</div>'
    ].join('')),

    /*
     * Renders the comment view.
     *
     * After rendering, this will queue up a load of the diff fragment
     * to display. The view will show a spinner until the fragment has
     * loaded.
     */
    render: function() {
        var fileDiffID = this.model.get('fileDiffID'),
            interFileDiffID = this.model.get('interFileDiffID');

        BaseCommentView.prototype.render.call(this);

        this.options.diffQueue.queueLoad(
            this.model.id,
            interFileDiffID ? fileDiffID + '-' + interFileDiffID
                            : fileDiffID);

        return this;
    },

    /*
     * Renders the thumbnail.
     */
    renderThumbnail: function() {
        var interFileDiff = this.model.get('interFileDiff');

        return $(this.thumbnailTemplate(_.defaults({
            numLines: this.model.getNumLines(),
            fileDiff: this.model.get('fileDiff').attributes,
            interFileDiff: interFileDiff ? interFileDiff.attributes : {}
        }, this.model.attributes)));
    }
});


/*
 * Displays a view for file attachment comments.
 */
FileAttachmentCommentView = BaseCommentView.extend({
    thumbnailTemplate: _.template([
        '<div class="file-attachment">',
        ' <span class="filename">',
        '  <img src="<%- fileAttachment.iconURL %>" />',
        '  <a href="<%- reviewURL %>"><%- linkText %></a>',
        ' </span>',
        ' <div class="thumbnail"><%= thumbnailHTML %></div>',
        '</div>'
    ].join('')),

    /*
     * Renders the thumbnail.
     */
    renderThumbnail: function() {
        return $(this.thumbnailTemplate(_.defaults({
            fileAttachment: this.model.get('fileAttachment').attributes
        }, this.model.attributes)));
    }
});


/*
 * Displays a view for screenshot comments.
 */
ScreenshotCommentView = BaseCommentView.extend({
    thumbnailTemplate: _.template([
        '<div class="screenshot">',
        ' <span class="filename">',
        '  <a href="<%- screenshot.reviewURL %>"><%- displayName %></a>',
        ' </span>',
        ' <img src="<%= thumbnailURL %>" width="<%= width %>" ',
        '      height="<%= height %>" alt="<%- displayName %>" />',
        '</div>'
    ].join('')),

    /*
     * Renders the thumbnail.
     */
    renderThumbnail: function() {
        var screenshot = this.model.get('screenshot');

        return $(this.thumbnailTemplate(_.defaults({
            screenshot: screenshot.attributes,
            displayName: screenshot.getDisplayName()
        }, this.model.attributes)));
    }
});


/*
 * Creates a dialog for modifying a draft review.
 *
 * This provides editing capabilities for creating or modifying a new
 * review. The list of comments are retrieved from the server, providing
 * context for the comments.
 */
RB.ReviewDialogView = Backbone.View.extend({
    id: 'review-form-comments',
    className: 'review',

    template: _.template([
        '<div class="edit-field">',
        ' <a class="markdown-info" href="<%- markdownDocsURL %>"',
        '    target="_blank"><%- markdownText %></a>',
        ' <input id="id_shipit" type="checkbox" />',
        ' <label for="id_shipit"><%- shipItText %></label>',
        '</div>',
        '<div class="review-dialog-hooks-container"></div>',
        '<div class="edit-field">',
        ' <div class="body-top"></div>',
        ' <span class="enable-markdown">',
        '  <input id="enable_body_top_markdown" type="checkbox" />',
        '  <label for="enable_body_top_markdown">',
        '<%- enableMarkdownText %></label>',
        ' </span>',
        '</div>',
        '<ul class="comments"></ul>',
        '<div class="spinner"></div>',
        '<div class="edit-field" id="body_bottom_fields">',
        ' <div class="body-bottom"></div>',
        ' <span class="enable-markdown">',
        '  <input id="enable_body_bottom_markdown" type="checkbox" />',
        '  <label for="enable_body_bottom_markdown">',
        '<%- enableMarkdownText %></label>',
        ' </span>',
        '</div>'
    ].join('')),

    /*
     * Initializes the review dialog.
     */
    initialize: function() {
        var reviewRequest = this.model.get('parentObject');

        this._$comments = null;
        this._$shipIt = null;
        this._$dlg = null;
        this._$buttons = null;
        this._$spinner = null;
        this._bodyTopEditor = null;
        this._bodyBottomEditor = null;
        this._$bodyBottomFields = null;

        this._commentViews = [];
        this._hookViews = [];

        this._diffQueue = new RB.DiffFragmentQueueView({
            containerPrefix: 'review_draft_comment_container',
            reviewRequestPath: reviewRequest.get('reviewURL'),
            queueName: 'review_draft_diff_comments'
        });

        this._diffCommentsCollection = new RB.ResourceCollection([], {
            model: RB.DiffComment,
            parentResource: this.model,
            extraQueryData: {
                'order-by': 'filediff,first_line'
            }
        });

        this.listenTo(this._diffCommentsCollection, 'add', function(comment) {
            this._renderComment(new DiffCommentView({
                model: comment,
                diffQueue: this._diffQueue
            }));
        });

        this._fileAttachmentCommentsCollection = new RB.ResourceCollection([], {
            model: RB.FileAttachmentComment,
            parentResource: this.model
        });

        this.listenTo(this._fileAttachmentCommentsCollection, 'add',
                      function(comment) {
            this._renderComment(new FileAttachmentCommentView({
                model: comment
            }));
        });

        this._screenshotCommentsCollection = new RB.ResourceCollection([], {
            model: RB.ScreenshotComment,
            parentResource: this.model
        });

        this.listenTo(this._screenshotCommentsCollection, 'add',
                      function(comment) {
            this._renderComment(new ScreenshotCommentView({
                model: comment
            }));
        });

        this._defaultUseRichText =
            RB.UserSession.instance.get('defaultUseRichText');

        if (this._defaultUseRichText) {
            this.model.set({
                forceTextType: 'markdown',
                includeTextTypes: 'raw'
            });

            this._queryData = {
                'force-text-type': 'markdown',
                'include-text-types': 'raw'
            };
        } else {
            this._queryData = {
                'force-text-type': undefined,
                'include-text-types': undefined
            };
        }

        this.options.reviewRequestEditor.incr('editCount');
    },

    /*
     * Removes the dialog from the DOM.
     *
     * This will remove all the extension hook views from the dialog,
     * and then remove the dialog itself.
     */
    remove: function() {
        _.each(this._hookViews, function(hookView) {
            hookView.remove();
        });

        this._hookViews = [];

        _super(this).remove.call(this);
    },

    /*
     * Closes the review dialog.
     *
     * The dialog will be removed from the screen, and the "closed"
     * event will be triggered.
     */
    close: function() {
        this.options.reviewRequestEditor.decr('editCount');
        this._$dlg.modalBox('destroy');
        this.trigger('closed');

        this.remove();
    },

    /*
     * Renders the dialog.
     *
     * The dialog will be shown on the screen, and the comments from
     * the server will begin loading and rendering.
     */
    render: function() {
        var $hooksContainer;

        this.$el.html(this.template({
            shipItText: gettext('Ship It'),
            markdownDocsURL: MANUAL_URL + 'users/markdown/',
            markdownText: gettext('Markdown Reference'),
            enableMarkdownText: gettext('Enable Markdown')
        }));

        this._$shipIt = this.$('#id_shipit');
        this._$comments = this.$el.children('.comments');
        this._$spinner = this.$el.children('.spinner');
        this._$bodyBottomFields = this.$el.children('#body_bottom_fields');

        $hooksContainer = this.$('.review-dialog-hooks-container');

        RB.ReviewDialogHook.each(function(hook) {
            var HookView = hook.get('viewType'),
                hookView = new HookView({
                    model: this.model
                });

            this._hookViews.push(hookView);

            $hooksContainer.append(hookView.$el);
            hookView.render();
        }, this);

        this._bodyTopEditor = new RB.TextEditorView({
            el: this.$('.body-top'),
            bindRichText: {
                model: this.model,
                attrName: 'bodyTopRichText'
            }
        });
        this._bodyTopEditor.render();
        this._bodyTopEditor.show();
        this._bodyTopEditor.bindRichTextCheckbox(
            this.$('#enable_body_top_markdown'));

        this._bodyBottomEditor = new RB.TextEditorView({
            el: this.$('.body-bottom'),
            bindRichText: {
                model: this.model,
                attrName: 'bodyBottomRichText'
            }
        });
        this._bodyBottomEditor.render();
        this._bodyBottomEditor.hide();
        this._$bodyBottomFields.hide();
        this._bodyBottomEditor.bindRichTextCheckbox(
            this.$('#enable_body_bottom_markdown'));

        this.model.ready({
            data: this._queryData,
            ready: function() {
                var bodyBottom,
                    bodyTop;

                this._renderDialog();

                if (this.model.isNew()) {
                    this._$spinner.remove();
                    this._$spinner = null;
                } else {
                    bodyBottom = this.model.get('bodyBottom') || '';
                    bodyTop = this.model.get('bodyTop') || '';

                    this._bodyBottomEditor.setText(bodyBottom);
                    this._bodyTopEditor.setText(bodyTop);
                    this._$shipIt.prop('checked', this.model.get('shipIt'));

                    this._loadComments();
                }
            }
        }, this);

        return this;
    },

    /*
     * Loads the comments from the server.
     *
     * This will begin chaining together the loads of each set of
     * comment types. Each loaded comment will be rendered to the
     * dialog once loaded.
     */
    _loadComments: function() {
        var collections = [
            this._screenshotCommentsCollection,
            this._fileAttachmentCommentsCollection,
            this._diffCommentsCollection
        ];

        this._loadCommentsFromCollection(collections, function() {
            this._$spinner.remove();
            this._$spinner = null;

            if (this._commentViews.length > 0) {
                /*
                 * We only display the bottom textarea if we have
                 * comments. Otherwise, it's weird to have both
                 * textareas visible with nothing inbetween.
                 */
                this._$bodyBottomFields.show();
                this._bodyBottomEditor.show();
            }
        });
    },

    /*
     * Loads the comments from a collection.
     *
     * This is part of the load comments flow. The list of remaining
     * collections are passed, and the first one will be removed
     * from the list and loaded.
     */
    _loadCommentsFromCollection: function(collections, onDone) {
        var collection = collections.shift();

        if (collection) {
            collection.fetchAll({
                data: this._queryData,
                success: function() {
                    if (collection === this._diffCommentsCollection) {
                        this._diffQueue.loadFragments();
                    }

                    this._loadCommentsFromCollection(collections, onDone);
                },
                error: function(rsp) {
                    // TODO: Provide better error output.
                    alert(rsp.errorText);
                }
            }, this);
        } else {
            onDone.call(this);
        }
    },

    /*
     * Renders a comment to the dialog.
     */
    _renderComment: function(view) {
        this._commentViews.push(view);
        view.$el.appendTo(this._$comments);
        view.render();
    },

    /*
     * Renders the dialog.
     *
     * This will create and render a dialog to the screen, adding
     * this view's element as the child.
     */
    _renderDialog: function() {
        var reviewRequest = this.model.get('parentObject');

        this._$dlg = $('<div/>')
            .attr('id', 'review-form')
            .append(this.$el)
            .modalBox({
                container: this.options.container || 'body',
                boxID: 'review-form-modalbox',
                title: gettext('Review for: ') + reviewRequest.get('summary'),
                stretchX: true,
                stretchY: true,
                buttons: [
                    $('<input type="button"/>')
                        .val(gettext('Publish Review'))
                        .click(_.bind(function() {
                            this._saveReview(true);
                            return false;
                        }, this)),

                    $('<input type="button"/>')
                        .val(gettext('Discard Review'))
                        .click(_.bind(this._onDiscardClicked, this)),

                    $('<input type="button"/>')
                        .val(gettext('Cancel'))
                        .click(_.bind(function() {
                            this.close();
                            return false;
                        }, this)),

                    $('<input type="button"/>')
                        .val(gettext('Save'))
                        .click(_.bind(function() {
                            this._saveReview();
                            return false;
                        }, this))
                ]
            })
            .keypress(function(e) { e.stopPropagation(); })
            .attr('scrollTop', 0)
            .trigger('ready');

        /* Must be done after the dialog is rendered. */
        this._$buttons = this._$dlg.modalBox('buttons');
        this._bodyTopEditor.focus();
    },


    /*
     * Handler for the Discard Review button.
     *
     * Prompts the user to confirm that they want the review discarded.
     * If they confirm, the review will be discarded.
     */
    _onDiscardClicked: function() {
        var model = this.model,
            self = this;

        $('<p/>')
            .text(gettext('If you discard this review, all related comments will be permanently deleted.'))
            .modalBox({
                title: gettext('Are you sure you want to discard this review?'),
                buttons: [
                    $('<input type="button"/>')
                        .val(gettext('Cancel')),
                    $('<input type="button"/>')
                        .val(gettext('Discard'))
                        .click(function() {
                            self.close();
                            model.destroy({
                                success: function() {
                                    RB.DraftReviewBannerView.instance
                                        .hideAndReload();
                                }
                            });
                        })
                ]
            });

        return false;
    },

    /*
     * Saves the review.
     *
     * This will save all the modified comments and the review fields.
     *
     * First, this loops over every comment and checks which needs
     * to be saved. It then adds each save operation to a queue, to be
     * performed later.
     *
     * The review saving or publishing is then added to the same queue,
     * followed by closing the dialog and showing/hiding the review
     * banner (depending on whether this is publishing).
     *
     * Once the queue contains all the operations we need to make,
     * it's executed. The result is a saved and possibly published
     * review.
     */
    _saveReview: function(publish) {
        this._$buttons.prop('disabled');

        $.funcQueue('reviewForm').clear();

        _.each(this._commentViews, function(view) {
            if (view.needsSave()) {
                $.funcQueue('reviewForm').add(function() {
                    view.save({
                        success: function() {
                            $.funcQueue('reviewForm').next();
                        }
                    });
                });
            }
        });

        $.funcQueue('reviewForm').add(function() {
            var saveFunc = publish ? this.model.publish : this.model.save;

            this.model.set({
                shipIt: this._$shipIt.prop('checked'),
                bodyTop: this._bodyTopEditor.getText(),
                bodyBottom: this._bodyBottomEditor.getText(),
                bodyTopRichText: this._bodyTopEditor.richText,
                bodyBottomRichText: this._bodyBottomEditor.richText
            });

            saveFunc.call(this.model, {
                success: function() {
                    $.funcQueue('reviewForm').next();
                },
                error: function() {
                    console.log(arguments);
                }
            });
        }, this);

        $.funcQueue('reviewForm').add(function() {
            var reviewBanner = RB.DraftReviewBannerView.instance;

            this.close();

            if (reviewBanner) {
                if (publish) {
                    reviewBanner.hideAndReload();
                } else {
                    reviewBanner.show();
                }
            }
        }, this);

        $.funcQueue('reviewForm').start();
    }
}, {
    /*
     * Add some useful singletons to ReviewDialogView for managing the
     * review dialog.
     */

    _instance: null,

    /*
     * Creates a ReviewDialogView.
     *
     * Only one is allowed on the screen at any given time.
     */
    create: function(options) {
        var instance = RB.ReviewDialogView._instance,
            reviewRequestEditor = options.reviewRequestEditor,
            dlg;

        options = options || {};

        console.assert(!instance, 'A ReviewDialogView is already opened');
        console.assert(options.review, 'A review must be specified');

        dlg = new RB.ReviewDialogView({
            container: options.container,
            model: options.review,
            reviewRequestEditor: reviewRequestEditor
        });
        RB.ReviewDialogView._instance = dlg;

        dlg.render();

        dlg.on('closed', function() {
            RB.ReviewDialogView._instance = null;
        });

        return dlg;
    }
});


})();
