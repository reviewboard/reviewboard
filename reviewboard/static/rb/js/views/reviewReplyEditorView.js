/*
 * Handles editing a reply to a comment in a review.
 *
 * This will handle the "Add Comment" link and the draft banners for the
 * review.
 */
RB.ReviewReplyEditorView = Backbone.View.extend({
    draftCommentTemplate: _.template([
        '<li class="reply-comment draft editor" id="<%= id %>-item">',
        ' <dl>',
        '  <dt>',
        '   <label for="<%= id %>">',
        '    <a href="<%= userPageURL %>"><%- fullName %></a>',
        '   </label>',
        '  </dt>',
        '  <dd><pre id="<%= id %>"></pre></dd>',
        ' </dl>',
        '</li>'
    ].join('')),

    events: {
        'click .add_comment_link': '_onAddCommentClicked'
    },

    /*
     * Renders the comment section.
     *
     * If there were any draft comments found, then editors will be
     * created for them, the Add Comment link will be hidden.
     */
    render: function() {
        var $draftComments;

        this._$addCommentLink = this.$('.add_comment_link');
        this._$commentsList = this.$('.reply-comments');

        $draftComments = this._$commentsList.children('[id^=yourcomment_]');

        if ($draftComments.length !== 0) {
            this.model.set({
                commentID: $draftComments.data('comment-id'),
                hasDraft: true
            });
            this._createCommentEditor($draftComments.find('pre.reviewtext'));
            this._$addCommentLink.hide();
        }

        this.model.on('change:text', function(model, text) {
            var reviewRequest = this.model.get('review').get('parentObject');

            if (this._$editor) {
                this._$editor.html(
                    RB.linkifyText(text, reviewRequest.get('bugTrackerURL')));
            }
        }, this);

        this.model.on('resetState', function(model, hasDraft) {
            if (!hasDraft) {
                this._$item.fadeOut(_.bind(function() {
                    this._$item.remove();
                    this._$addCommentLink.fadeIn();
                }, this));
            }
        }, this);

        this.model.on('published discarded', function() {
            window.location = gReviewRequestPath;
        });
    },

    /*
     * Creates a new draft comment form and begins editing.
     */
    _createNewCommentForm: function() {
        var userSession = RB.UserSession.instance,
            contextID = this.model.get('contextID'),
            elID = 'yourcomment_' + this.model.get('review').id + '_' +
                                    this.model.get('contextType'),
            $draftComment,
            $editor;

        if (contextID) {
            elID += '_' + contextID;
        }

        elID += '_draft';

        $draftComment =
            $(this.draftCommentTemplate({
                id: elID,
                userPageURL: userSession.get('userPageURL'),
                fullName: userSession.get('fullName')
            }))
            .appendTo(this._$commentsList);

        $editor = $draftComment.find('#' + elID);
        this._createCommentEditor($editor);

        $editor.inlineEditor('startEdit');

        this._$addCommentLink.hide();
    },

    /*
     * Creates a comment editor for an element.
     */
    _createCommentEditor: function($editor) {
        var pageEditState = this.options.pageEditState;

        this._$item = $('#' + $editor[0].id + '-item');
        this._$editor = $editor;

        $editor
            .inlineEditor({
                cls: 'inline-comment-editor',
                editIconPath: STATIC_URLS['rb/images/edit.png'],
                notifyUnchangedCompletion: true,
                multiline: true
            })
            .on({
                beginEdit: function() {
                    pageEditState.incr('editCount');
                },
                complete: _.bind(function(e, value) {
                    pageEditState.decr('editCount');
                    this.model.set('text', value);
                    this.model.save();
                }, this),
                cancel: _.bind(function() {
                    pageEditState.decr('editCount');
                    this.model.resetStateIfEmpty();
                }, this)
            });
    },

    /*
     * Handler for when the Add Comment link is clicked
     *
     * Creates a new comment form.
     */
    _onAddCommentClicked: function() {
        this._createNewCommentForm();
        return false;
    }
});
