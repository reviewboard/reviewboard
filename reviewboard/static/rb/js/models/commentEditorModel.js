/*
 * Represents the state for editing a new or existing draft comment.
 *
 * From here, a comment can be created, edited, or deleted.
 *
 * This will provide state on what actions are available on a comment,
 * informative text, dirty states, existing published comments on the
 * same region this comment is on, and more.
 */
RB.CommentEditor = Backbone.Model.extend({
    defaults: {
        canDelete: false,
        canEdit: gUserAuthenticated,
        canSave: false,
        editing: false,
        comment: null,
        dirty: false,
        openIssue: gOpenAnIssue,
        publishedComments: [],
        publishedCommentsType: null,
        statusText: '',
        text: ''
    },

    initialize: function() {
        this.on('change:comment', function(model, comment) {
            var oldComment = model.previous('comment');

            if (oldComment) {
                oldComment.deleteIfEmpty();
            }

            this.set('statusText', '');

            if (comment) {
                comment.ready(function() {
                    this.set({
                        dirty: false,
                        openIssue: comment.loaded
                                   ? comment.issue_opened
                                   : this.defaults.openIssue,
                        text: comment.text
                    });
                }, this);
            }
        }, this);

        this.on('change:dirty', function(model, dirty) {
            if (dirty) {
                gEditCount++;
            } else {
                gEditCount--
            }

            this.set('statusText',
                     dirty ? 'This comment has unsaved changes.' : '');
        }, this);

        this.on('change:openIssue change:text', function() {
            if (this.get('editing')) {
                this.set('dirty', true);
                this._updateState();
            }
        }, this);

        this._updateState();
    },

    /*
     * Sets the editor to begin editing a new or existing comment.
     */
    beginEdit: function() {
        console.assert(this.get('canEdit'),
                       'beginEdit() called when canEdit is false.');
        console.assert(this.get('comment'),
                       'beginEdit() called when no comment was first set.');

        this.set({
            dirty: false,
            editing: true
        });

        this._updateState();
    },

    /*
     * Deletes the current comment, if it can be deleted.
     *
     * This requires that there's a saved comment to delete.
     *
     * The editor will be marked as closed, requiring a new call to beginEdit.
     */
    deleteComment: function() {
        var comment = this.get('comment');

        console.assert(this.get('canDelete'),
                       'deleteComment() called when canDelete is false.');
        comment.deleteComment();

        this.trigger('deleted');

        this.close();
    },

    /*
     * Cancels editing of a comment.
     *
     * If there's a saved comment and it's been made empty, it will end
     * up being deleted. Then this editor will be marked as closed,
     * requiring a new call to beginEdit.
     */
    cancel: function() {
        var comment = this.get('comment');

        if (comment) {
            comment.deleteIfEmpty();
            this.trigger('canceled');
        }

        this.close();
    },

    /*
     * Closes editing of the comment.
     *
     * The comment state will be reset, and the "closed" event will be
     * triggered.
     *
     * To edit a comment again after closing it, the proper state must be
     * set again and beginEdit must be called.
     */
    close: function() {
        /* Set this first, to prevent dirty firing. */
        this.set('editing', false);

        this.set({
            comment: null,
            dirty: false,
            text: ''
        });

        this.trigger('closed');
    },

    /*
     * Saves the comment.
     *
     * If this is a new comment, it will be created on the server.
     * Otherwise, the existing comment will be updated.
     *
     * The editor will not automatically be marked as closed. That is up
     * to the caller.
     */
    save: function() {
        var comment = this.get('comment');

        console.assert(this.get('canSave'),
                       'save() called when canSave is false.');

        comment.setText(this.get('text'));
        comment.issue_opened = this.get('openIssue');
        comment.save();

        this.set('dirty', false);

        this.trigger('saved');
    },

    /*
     * Updates the capability states of the editor.
     *
     * Some of the can* properties will change to reflect the various
     * actions that can be performed with the editor.
     */
    _updateState: function() {
        var canEdit = this.get('canEdit'),
            editing = this.get('editing'),
            comment = this.get('comment');

        this.set({
            canDelete: canEdit && editing && comment && comment.loaded,
            canSave: canEdit && editing && this.get('text') !== ''
        });
    }
});
