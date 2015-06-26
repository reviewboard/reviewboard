/*
 * Handles editing a reply to a comment in a review.
 *
 * This will handle the "New Comment" link and the draft banners for the
 * review.
 */
RB.ReviewReplyEditorView = Backbone.View.extend({
    commentTemplate: _.template([
        '<li <% if (isDraft) { %>class="draft"<% } %>',
        '    <% if (commentID) { %>data-comment-id="<%= commentID %>"<% } %>>',
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
        '  <dd><pre id="<%= id %>" class="reviewtext">',
        '<%- text %></pre></dd>',
        ' </dl>',
        '</li>'
    ].join('')),

    events: {
        'click .add_comment_link': '_onAddCommentClicked'
    },

    initialize: function() {
        this._$addCommentLink = null;
        this._$draftComment = null;
        this._$editor = null;
        this._$commentsList = null;
    },

    /*
     * Renders the comment section.
     *
     * If there were any draft comments found, then editors will be
     * created for them, the New Comment link will be hidden.
     */
    render: function() {
        var $draftComment,
            $reviewText,
            $time;

        this._$addCommentLink = this.$('.add_comment_link');
        this._$commentsList = this.$('.reply-comments');

        /* See if there's a draft comment to import from the page. */
        $draftComment = this._$commentsList.children('.draft');

        if ($draftComment.length !== 0) {
            $time = $draftComment.find('time');
            $reviewText = $draftComment.find('.reviewtext');

            this.model.set({
                commentID: $draftComment.data('comment-id'),
                text: $reviewText.html(),
                timestamp: new Date($time.attr('datetime')),
                richText: $reviewText.hasClass('rich-text'),
                hasDraft: true
            });
            this._createCommentEditor($draftComment);
        }

        this.listenTo(this.model, 'textUpdated', function() {
            var reviewRequest = this.model.get('review').get('parentObject');

            if (this._$editor) {
                RB.formatText(this._$editor, {
                    newText: this.model.get('text'),
                    richText: this.model.get('richText'),
                    bugTrackerURL: reviewRequest.get('bugTrackerURL')
                });
            }
        });

        this.model.on('resetState', function() {
            if (this._$draftComment) {
                this._$draftComment.fadeOut(_.bind(function() {
                    this._$draftComment.remove();
                    this._$draftComment = null;
                }, this));
            }

            this._$addCommentLink.fadeIn();
        }, this);

        this.model.on('published', this._onPublished, this);
    },

    /*
     * Opens the comment editor for a new comment.
     */
    openCommentEditor: function() {
        this._createCommentEditor(this._makeCommentElement());
        this._$editor.inlineEditor('startEdit');
    },

    /*
     * Creates a comment editor for an element.
     */
    _createCommentEditor: function($draftComment) {
        var pageEditState = this.options.pageEditState;

        this._$draftComment = $draftComment;

        this._$editor = $draftComment.find('pre.reviewtext');
        this._$editor
            .inlineEditor(
                _.extend({
                    cls: 'inline-comment-editor',
                    editIconClass: 'rb-icon rb-icon-edit',
                    notifyUnchangedCompletion: true,
                    multiline: true,
                    hasRawValue: true,
                    rawValue: this._$editor.data('raw-value') || ''
                },
                RB.TextEditorView.getInlineEditorOptions({
                    richText: this._$editor.hasClass('rich-text')
                }))
            )
            .removeAttr('data-raw-value')
            .on({
                beginEdit: function() {
                    if (pageEditState) {
                        pageEditState.incr('editCount');
                    }
                },
                complete: _.bind(function(e, value) {
                    var textEditor = RB.TextEditorView.getFromInlineEditor(
                        this._$editor);

                    if (pageEditState) {
                        pageEditState.decr('editCount');
                    }

                    this.model.set({
                        text: value,
                        richText: textEditor.richText
                    });
                    this.model.save();
                }, this),
                cancel: _.bind(function() {
                    if (pageEditState) {
                        pageEditState.decr('editCount');
                    }

                    this.model.resetStateIfEmpty();
                }, this)
            });

        this._$addCommentLink.hide();
    },

    /*
     * Creates an element for the comment form.
     */
    _makeCommentElement: function(options) {
        var userSession = RB.UserSession.instance,
            reviewRequest = this.model.get('review').get('parentObject'),
            now,
            $el;

        options = options || {};
        now = options.now || moment().zone(userSession.get('timezoneOffset'));

        $el = $(this.commentTemplate(_.extend({
                id: _.uniqueId('draft_comment_'),
                text: '',
                commentID: null,
                userPageURL: userSession.get('userPageURL'),
                fullName: userSession.get('fullName'),
                isDraft: true,
                timestampISO: now.format(),

                /*
                 * Note that we format the a.m./p.m. this way to match
                 * what's coming from the Django templates.
                 */
                timestamp: now.format('MMMM Do, YYYY, h:mm ') +
                           (now.hour() < 12 ? 'a.m.' : 'p.m.')
            }, options)))
            .find('.user')
                .user_infobox()
            .end()
            .find('time.timesince')
                .timesince()
            .end()
            .appendTo(this._$commentsList);

        if (options.text) {
            RB.formatText($el.find('.reviewtext'), {
                newText: options.text,
                richText: options.richText,
                bugTrackerURL: reviewRequest.get('bugTrackerURL')
            });
        }

        return $el;
    },

    /*
     * Handler for when the New Comment link is clicked.
     *
     * Creates a new comment form and editor.
     */
    _onAddCommentClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this.openCommentEditor();
    },

    /*
     * Handler for when the reply is published.
     *
     * Updates the draft comment to be a standard comment, and brings back
     * the New Comment link.
     */
    _onPublished: function() {
        if (this._$draftComment) {
            this._$draftComment.replaceWith(this._makeCommentElement({
                commentID: this.model.get('commentID'),
                text: this.model.get('text'),
                richText: this.model.get('richText'),
                isDraft: false
            }));

            this._$draftComment = null;
        }
    }
});
