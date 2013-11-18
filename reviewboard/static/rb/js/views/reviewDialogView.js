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
        '</div>'
    ].join('')),

    initialize: function() {
        this.$issueOpened = null;
        this.textEditor = null;

        this._origIssueOpened = this.model.get('issueOpened');
        this._origExtraData = _.clone(this.model.get('extraData'));
        this._hookViews = [];
    },

    remove: function() {
        _.each(this._hookViews, function(hookView) {
            hookView.remove();
        });

        this._hookViews = [];

        _.super(this).remove.call(this);
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

        return this.model.get('text') !== newValue ||
               this.model.get('issueOpened') !== newIssueOpened ||
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
            richText: true,
            text: this.textEditor.getText()
        });
        this.model.save(options);
    },

    /*
     * Renders the comment view.
     */
    render: function() {
        var $editFields,
            text = this.model.get('text');

        this.$el
            .append(this.renderThumbnail())
            .append($(this.editorTemplate({
                text: this.model.get('text'),
                issueOpenedID: _.uniqueId('issue-opened'),
                openAnIssueText: gettext('Open an issue')
            })));

        this.textEditor = new RB.MarkdownEditorView({
            el: this.$('.comment-text-field')
        });
        this.textEditor.render();
        this.textEditor.show();

        this.$issueOpened = this.$('.issue-opened')
            .prop('checked', this.model.get('issueOpened'));

        if (!this.model.get('richText')) {
            /*
             * If this comment is modified and saved, it'll be saved as
             * Markdown. Escape it so that nothing currently there is
             * unintentionally interpreted as Markdown later.
             */
            text = RB.escapeMarkdown(text);
        }

        this.textEditor.setText(text);

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
        ' <input id="id_shipit" type="checkbox" />',
        ' <label for="id_shipit"><%- shipItText %></label>',
        '</div>',
        '<div class="edit-field">',
        ' <div class="body-top"></div>',
        '</div>',
        '<ul class="comments"></ul>',
        '<div class="spinner"></div>',
        '<div class="edit-field">',
        ' <div class="body-bottom"></div>',
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

        this._commentViews = [];

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

        this.options.reviewRequestEditor.incr('editCount');
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
        this.$el.html(this.template({
            shipItText: gettext('Ship It')
        }));

        this._$shipIt = this.$('#id_shipit');
        this._$comments = this.$el.children('.comments');
        this._$spinner = this.$el.children('.spinner');

        this._bodyTopEditor = new RB.MarkdownEditorView({
            el: this.$('.body-top')
        });
        this._bodyTopEditor.render();
        this._bodyTopEditor.show();

        this._bodyBottomEditor = new RB.MarkdownEditorView({
            el: this.$('.body-bottom')
        });
        this._bodyBottomEditor.render();
        this._bodyBottomEditor.hide();

        this.model.ready({
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

                    if (!this.model.get('richText')) {
                        /*
                         * When saving, these will convert to Markdown,
                         * so escape them before-hand.
                         */
                        bodyBottom = RB.escapeMarkdown(bodyBottom);
                        bodyTop = RB.escapeMarkdown(bodyTop);
                    }

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
                        .click(_.bind(function() {
                            this.close();
                            this.model.destroy({
                                success: function() {
                                    RB.DraftReviewBannerView.instance
                                        .hideAndReload();
                                }
                            });

                            return false;
                        }, this)),

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
            this.model.set({
                shipIt: this._$shipIt.prop('checked'),
                bodyTop: this._bodyTopEditor.getText(),
                bodyBottom: this._bodyBottomEditor.getText(),
                public: publish,
                richText: true
            });

            this.model.save({
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
