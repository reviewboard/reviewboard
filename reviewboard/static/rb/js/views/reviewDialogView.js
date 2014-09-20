(function() {


var BaseCommentView,
    DiffCommentView,
    FileAttachmentCommentView,
    ScreenshotCommentView,
    HeaderFooterCommentView;


/*
 * Base class for displaying a comment in the review dialog.
 */
BaseCommentView = Backbone.View.extend({
    tagName: 'li',

    thumbnailTemplate: '',

    editorTemplate: _.template([
        '<div class="edit-fields">',
        ' <div class="edit-field">',
        '  <div class="comment-text-field">',
        '   <dl>',
        '    <dt>',
        '     <label for="<%= id %>">',
        '      <a href="<%= userPageURL %>" class="user"><%- fullName %></a>',
        '<% if (timestamp) { %>',
        '      <span class="timestamp">',
        '       <time class="timesince" datetime="<%= timestampISO %>">',
        '<%= timestamp %></time> (<%= timestamp %>)',
        '      </span>',
        '<% } %>',
        '     </label>',
        '    </dt>',
        '    <dd><pre id="<%= id %>" class="reviewtext rich-text" ',
        '             data-rich-text="true"><%- text %></pre></dd>',
        '   </dl>',
        '  </div>',
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
        this.$editor = null;

        this._hookViews = [];
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
     * The comment will need to be saved if the inline editor is currently
     * open.
     */
    needsSave: function() {
        return (this.$editor.inlineEditor('dirty') ||
                !_.isEqual(this.model.get('extraData'), this._origExtraData));
    },

    /*
     * Saves the final state of the view.
     *
     * Saves the inline editor and notifies the caller when the model is
     * synced.
     */
    save: function(options) {
        /*
         * If the inline editor needs to be saved, ask it to do so. This will
         * call this.model.save(). If it does not, just save the model
         * directly.
         */
        if (this.$editor.inlineEditor('dirty')) {
            this.model.once('sync', function() {
                options.success();
            });

            this.$editor.inlineEditor('submit');
        } else {
            this.model.save(options);
        }
    },

    /*
     * Renders the comment view.
     */
    render: function() {
        var $editFields,
            text = this.model.get('text'),
            userSession = RB.UserSession.instance,
            now = moment().zone(userSession.get('timezoneOffset'));

        this.$el
            .addClass('draft')
            .append(this.renderThumbnail())
            .append($(this.editorTemplate({
                fullName: userSession.get('fullName'),
                id: _.uniqueId('draft_comment_'),
                issueOpenedID: _.uniqueId('issue-opened'),
                openAnIssueText: gettext('Open an issue'),
                text: text,
                timestamp: RB.FormatTimestamp(now),
                timestampISO: now.format(),
                userPageURL: userSession.get('userPageURL')
            })))
            .find('time.timesince')
                .timesince()
            .end();

        this.$issueOpened = this.$('.issue-opened')
            .prop('checked', this.model.get('issueOpened'))
            .change(_.bind(function() {
                this.model.set('issueOpened',
                               this.$issueOpened.prop('checked'));
                this.model.save();
            }, this));

        $editFields = this.$('.edit-fields');

        this.$editor = this.$('pre.reviewtext')
            .inlineEditor(_.extend({
                cls: 'inline-comment-editor',
                editIconClass: 'rb-icon rb-icon-edit',
                notifyUnchangedCompletion: true,
                multiline: true
            }, RB.MarkdownEditorView.getInlineEditorOptions()))
            .on({
                complete: _.bind(function(e, value) {
                    this.model.set({
                        text: value,
                        richText: true
                    });
                    this.model.save();
                }, this),
                cancel: _.bind(function() {
                    this.$editor
                        .inlineEditor('buttons')
                        .find('.markdown-info')
                        .remove();
                }, this)
            });

        this.model.on('change:text', this.renderText, this);
        this.renderText(this.model, text);

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
    },

    /*
     * Renders the text for this comment.
     */
    renderText: function(model, text) {
        var reviewRequest = this.model.get('parentObject').get('parentObject');

        if (this.$editor) {
            RB.formatText(this.$editor, text,
                          reviewRequest.get('bugTrackerURL'));
        }
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
 * The header or footer for a review.
 */
HeaderFooterCommentView = Backbone.View.extend({
    editorTemplate: _.template([
        '<div class="add-link-container">',
        ' <a href="#" class="add-link"><%- linkText %></a>',
        '</div>',
        '<div class="comment-text-field">',
        ' <dl>',
        '  <dt>',
        '   <label for="<%= id %>">',
        '    <a href="<%= userPageURL %>" class="user"><%- fullName %></a>',
        '<% if (timestamp) { %>',
        '    <span class="timestamp">',
        '     <time class="timesince" datetime="<%= timestampISO %>">',
        '<%= timestamp %></time> (<%= timestamp %>)',
        '    </span>',
        '<% } %>',
        '   </label>',
        '  </dt>',
        '  <dd><pre id="<%= id %>" class="reviewtext rich-text" ',
        '           data-rich-text="true"><%- text %></pre></dd>',
        ' </dl>',
        '</div>'
    ].join('')),

    events: {
        'click .add-link': 'openEditor'
    },

    initialize: function(options) {
        this.$editor = null;
        this.propertyName = options.propertyName;
        this.linkText = options.linkText;
    },

    setLinkText: function(linkText) {
        this.$('.add-link').text(linkText);
    },

    /*
     * Renders the view.
     */
    render: function() {
        var text = this.model.get(this.propertyName),
            userSession = RB.UserSession.instance,
            now = moment().zone(userSession.get('timezoneOffset'));

        this.$el
            .addClass('draft')
            .append($(this.editorTemplate({
                fullName: userSession.get('fullName'),
                id: this.propertyName,
                linkText: this.linkText,
                text: text || '',
                timestamp: RB.FormatTimestamp(now),
                timestampISO: now.format(),
                userPageURL: userSession.get('userPageURL')
            })))
            .find('time.timesince')
                .timesince()
            .end();

        this.$editor = this.$('pre.reviewtext')
            .inlineEditor(_.extend({
                cls: 'inline-comment-editor',
                editIconClass: 'rb-icon rb-icon-edit',
                notifyUnchangedCompletion: true,
                multiline: true
            }, RB.MarkdownEditorView.getInlineEditorOptions()))
            .on({
                complete: _.bind(function(e, value) {
                    this.model.set(this.propertyName, value);
                    this.model.set('richText', true);
                    this.model.save();
                }, this),
                cancel: _.bind(function() {
                    this.$editor
                        .inlineEditor('buttons')
                        .find('.markdown-info')
                        .remove();

                    if (!this.model.get(this.propertyName)) {
                        this._$editorContainer.hide();
                        this._$linkContainer.show();
                    }
                }, this)
            });

        this._$editorContainer = this.$('.comment-text-field');
        this._$linkContainer = this.$('.add-link-container');

        this.model.on('change:' + this.propertyName, this.renderText, this);
        this.renderText(this.model, text);
    },

    /*
     * Renders the text for this comment.
     */
    renderText: function(model, text) {
        var reviewRequest = this.model.get('parentObject');

        if (this.$editor) {
            if (text) {
                this._$editorContainer.show();
                this._$linkContainer.hide();
                RB.formatText(this.$editor, text,
                              reviewRequest.get('bugTrackerURL'));
            } else {
                this._$editorContainer.hide();
                this._$linkContainer.show();
            }
        }
    },

    /*
     * Returns whether or not the comment needs to be saved.
     *
     * The comment will need to be saved if the inline editor is currently
     * open.
     */
    needsSave: function() {
        return this.$editor.inlineEditor('dirty');
    },

    /*
     * Saves the final state of the view.
     */
    save: function(options) {
        this.model.once('sync', function() {
            options.success();
        });

        this.$editor.inlineEditor('submit');
    },

    /*
     * Opens the editor. This is used for the 'Add ...' link handler, as well
     * as for the default state of the dialog when there are no comments.
     */
    openEditor: function(ev) {
        this._$linkContainer.hide();
        this._$editorContainer.show();

        this.$editor.inlineEditor('startEdit');

        if (ev) {
            ev.preventDefault();
        }

        return false;
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
        '<div class="edit-field body-top"></div>',
        '<ul class="comments"></ul>',
        '<div class="spinner"></div>',
        '<div class="edit-field body-bottom"></div>'
    ].join('')),

    /*
     * Initializes the review dialog.
     */
    initialize: function() {
        var reviewRequest = this.model.get('parentObject');

        this._$comments = null;
        this._$dlg = null;
        this._$buttons = null;
        this._$spinner = null;
        this._$shipIt = null;

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
            addHeaderText: gettext('Add header'),
            addFooterText: gettext('Add footer'),
            shipItText: gettext('Ship It'),
            markdownDocsURL: MANUAL_URL + 'users/markdown/',
            markdownText: gettext('Markdown Reference')
        }));

        this._$comments = this.$('.comments');
        this._$spinner = this.$('.spinner');
        this._$shipIt = this.$('#id_shipit');

        this._bodyTopView = new HeaderFooterCommentView({
            model: this.model,
            el: this.$('.body-top'),
            propertyName: 'bodyTop',
            linkText: gettext('Add header')
        });

        this._bodyBottomView = new HeaderFooterCommentView({
            model: this.model,
            el: this.$('.body-bottom'),
            propertyName: 'bodyBottom',
            linkText: gettext('Add footer')
        });

        this.model.ready({
            ready: function() {
                this._renderDialog();
                this._bodyTopView.render();
                this._bodyBottomView.render();

                if (this.model.isNew()) {
                    this._$spinner.remove();
                    this._$spinner = null;

                    this._handleEmptyReview();
                    this._bodyTopView.openEditor();
                } else {
                    this._$shipIt
                        .prop('checked', this.model.get('shipIt'))
                        .change(_.bind(function() {
                            this.model.set('shipIt',
                                           this._$shipIt.prop('checked'));
                            this.model.save();
                        }, this));

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

            this._handleEmptyReview();
        });
    },

    /*
     * Properly set the view when the review is empty.
     */
    _handleEmptyReview: function() {
        if (this._commentViews.length === 0) {
            /*
             * We only display the bottom textarea if we have
             * comments. Otherwise, it's weird to have both
             * textareas visible with nothing inbetween.
             */
            this._bodyBottomView.$el.hide();
            this._bodyTopView.setLinkText(gettext('Add text'));
        }
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
                        .click(_.bind(this._onDiscardClicked, this)),

                    $('<input type="button"/>')
                        .val(gettext('Close'))
                        .click(_.bind(function() {
                            this._saveReview(false);
                            return false;
                        }, this))
                ]
            })
            .keypress(function(e) { e.stopPropagation(); })
            .attr('scrollTop', 0)
            .trigger('ready');

        /* Must be done after the dialog is rendered. */
        this._$buttons = this._$dlg.modalBox('buttons');
    },


    /*
     * Handler for the Discard Review button.
     *
     * Prompts the user to confirm that they want the review discarded.
     * If they confirm, the review will be discarded.
     */
    _onDiscardClicked: function () {
        var model = this.model,
            self = this;

        $('<p/>')
            .text(gettext('If you discard this review, all related comments will be permanently deleted.'))
            .modalBox({
                title: gettext('Are you sure you want to discard this review?'),
                buttons: [
                    $('<input type="button" value="' + gettext('Cancel') + '"/>'),
                    $('<input type="button" value="' + gettext('Discard') + '"/>')
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
     * First, this loops over all the comment editors and saves any which are
     * still in the editing phase.
     *
     * If requested, this will also publish the review (saving with
     * public=true).
     */
    _saveReview: function(publish) {
        this._$buttons.prop('disabled');

        $.funcQueue('reviewForm').clear();

        function maybeSave(view) {
            if (view.needsSave()) {
                $.funcQueue('reviewForm').add(function() {
                    view.save({
                        success: function() {
                            $.funcQueue('reviewForm').next();
                        }
                    });
                });
            }
        }

        maybeSave(this._bodyTopView);
        maybeSave(this._bodyBottomView);
        _.each(this._commentViews, maybeSave);

        $.funcQueue('reviewForm').add(function() {
            this.model.set({
                'public': publish,
                richText: true,
                shipIt: this._$shipIt.prop('checked')
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
