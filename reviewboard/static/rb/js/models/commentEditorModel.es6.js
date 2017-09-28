/**
 * Represents the state for editing a new or existing draft comment.
 *
 * From here, a comment can be created, edited, or deleted.
 *
 * This will provide state on what actions are available on a comment,
 * informative text, dirty states, existing published comments on the
 * same region this comment is on, and more.
 *
 * Attributes:
 *     canDelete (boolean):
 *         Whether the draft comment can be deleted.
 *
 *     canEdit (boolean):
 *         Whether the draft comment can be edited.
 *
 *     canSave (boolean):
 *         Whether the draft comment can be saved.
 *
 *     editing (boolean):
 *         True if the comment is currently being edited.
 *
 *     extraData (object):
 *         The draft state for the comment's extra data.
 *
 *     comment (RB.BaseComment):
 *         The comment model.
 *
 *     dirty (boolean):
 *         True if the draft comment has been edited but not saved.
 *
 *     openIssue (boolean):
 *         Whether the comment opens an issue.
 *
 *     publishedComments (Array of RB.BaseComment):
 *         The thread of previous comments that this draft is a reply to, if
 *         applicable.
 *
 *     publishedCommentsType (string):
 *         The type of comment that this draft is a reply to, if applicable.
 *
 *     reviewRequest (RB.ReviewRequest):
 *         The review request that the comment is on.
 *
 *     richText (boolean):
 *         Whether the comment is formatted in Markdown.
 *
 *     text (string):
 *         The comment's text.
 */
RB.CommentEditor = Backbone.Model.extend(_.defaults({
    /**
     * Return the default values for the model attributes.
     *
     * Returns:
     *     object:
     *     The default values for the attributes.
     */
    defaults() {
        const userSession = RB.UserSession.instance;

        return {
            canDelete: false,
            canEdit: undefined,
            canSave: false,
            editing: false,
            extraData: {},
            comment: null,
            dirty: false,
            openIssue: userSession.get('commentsOpenAnIssue'),
            publishedComments: [],
            publishedCommentsType: null,
            requireVerification: false, // TODO: add a user preference for this.
            reviewRequest: null,
            richText: userSession.get('defaultUseRichText'),
            text: '',
        };
    },

    /**
     * Initialize the comment editor.
     */
    initialize() {
        const reviewRequest = this.get('reviewRequest');

        this.on('change:comment', this._updateFromComment, this);
        this._updateFromComment();

        /*
         * Unless a canEdit value is explicitly given, we want to compute
         * the proper state.
         */
        if (this.get('canEdit') === undefined) {
            reviewRequest.on('change:hasDraft', this._updateCanEdit, this);
            this._updateCanEdit();
        }

        this.on('change:dirty', (model, dirty) => {
            const reviewRequestEditor = this.get('reviewRequestEditor');

            if (reviewRequestEditor) {
                if (dirty) {
                    reviewRequestEditor.incr('editCount');
                } else {
                    reviewRequestEditor.decr('editCount');
                }
            }
        });

        this.on(
            'change:openIssue change:requireVerification ' +
            'change:richText change:text',
            () => {
                if (this.get('editing')) {
                    this.set('dirty', true);
                    this._updateState();
                }
            });

        this._updateState();

        this._setupExtraData();
    },

    /**
     * Set the editor to begin editing a new or existing comment.
     */
    beginEdit() {
        console.assert(this.get('canEdit'),
                       'beginEdit() called when canEdit is false.');
        console.assert(this.get('comment'),
                       'beginEdit() called when no comment was first set.');

        this.set({
            dirty: false,
            editing: true,
        });

        this._updateState();
    },

    /**
     * Delete the current comment, if it can be deleted.
     *
     * This requires that there's a saved comment to delete.
     *
     * The editor will be marked as closed, requiring a new call to beginEdit.
     */
    deleteComment() {
        console.assert(this.get('canDelete'),
                       'deleteComment() called when canDelete is false.');

        const comment = this.get('comment');
        comment.destroy({
            success: () => {
                this.trigger('deleted');
                this.close();
            },
        });
    },

    /**
     * Cancel editing of a comment.
     *
     * If there's a saved comment and it's been made empty, it will end
     * up being deleted. Then this editor will be marked as closed,
     * requiring a new call to beginEdit.
     */
    cancel() {
        const comment = this.get('comment');

        this.off('change:comment', this._updateFromComment, this);

        if (comment) {
            comment.destroyIfEmpty();
            this.trigger('canceled');
        }

        this.close();
    },

    /**
     * Close editing of the comment.
     *
     * The comment state will be reset, and the "closed" event will be
     * triggered.
     *
     * To edit a comment again after closing it, the proper state must be
     * set again and beginEdit must be called.
     */
    close() {
        /* Set this first, to prevent dirty firing. */
        this.set('editing', false);

        this.set({
            comment: null,
            dirty: false,
            extraData: new RB.ExtraData(),
            text: '',
        });

        this.trigger('closed');
    },

    /**
     * Save the comment.
     *
     * If this is a new comment, it will be created on the server.
     * Otherwise, the existing comment will be updated.
     *
     * The editor will not automatically be marked as closed. That is up
     * to the caller.
     *
     * Args:
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         The context to use when calling callbacks.
     */
    save(options={}, context=undefined) {
        console.assert(this.get('canSave'),
                       'save() called when canSave is false.');

        const extraData =  _.clone(this.get('extraData'));
        extraData.require_verification = this.get('requireVerification');

        const comment = this.get('comment');
        comment.set({
            text: this.get('text'),
            issueOpened: this.get('openIssue'),
            extraData: extraData,
            richText: this.get('richText'),
            includeTextTypes: 'html,raw,markdown',
        });

        comment.save({
            success: () => {
                this.set('dirty', false);
                this.trigger('saved');

                if (_.isFunction(options.success)) {
                    options.success.call(context);
                }
            },

            error: _.isFunction(options.error)
                   ? options.error.bind(context)
                   : undefined,
        });
    },

    /**
     * Update the state of the editor from the currently set comment.
     */
    _updateFromComment() {
        const oldComment = this.previous('comment');
        const comment = this.get('comment');

        if (oldComment) {
            oldComment.destroyIfEmpty();
        }

        if (comment) {
            const defaultRichText = this.defaults().richText;

            /*
             * Set the attributes based on what we know at page load time.
             *
             * Note that it is *possible* that the comments will have changed
             * server-side since loading the page (if the user is reviewing
             * the same diff in two tabs). However, it's unlikely.
             *
             * Doing this before the ready() call ensures that we'll have the
             * text and state up-front and that it won't overwrite what the
             * user has typed after load.
             *
             * Note also that we'll always want to use our default richText
             * value if it's true, and we'll fall back on the comment's value
             * if false. This is so that we can keep a consistent experience
             * when the "Always edit Markdown by default" value is set.
             */
            this.set({
                dirty: false,
                extraData: comment.get('extraData'),
                openIssue: comment.get('issueOpened') === null
                           ? this.defaults().openIssue
                           : comment.get('issueOpened'),
                requireVerification: comment.requiresVerification(),
                richText: defaultRichText || !!comment.get('richText'),
            });

            /*
             * We'll try to set the one from the appropriate text fields, if it
             * exists and is not empty. If we have this, then it came from a
             * previous save. If we don't have it, we'll fall back to "text",
             * which should be normalized content from the initial page load.
             */
            const textFields = (comment.get('richText') || !defaultRichText
                                ? comment.get('rawTextFields')
                                : comment.get('markdownTextFields'));

            this.set('text',
                     !_.isEmpty(textFields)
                     ? textFields.text
                     : comment.get('text'));

            comment.ready({
                ready: this._updateState,
            }, this);
        }
    },

    /**
     * Update the canEdit state of the editor.
     *
     * This is based on the authentication state of the user, and
     * whether or not there's an existing draft for the review request.
     */
    _updateCanEdit() {
        const reviewRequest = this.get('reviewRequest');
        const userSession = RB.UserSession.instance;

        this.set('canEdit',
                 userSession.get('authenticated') &&
                 !userSession.get('readOnly') &&
                 !reviewRequest.get('hasDraft'));
    },

    /**
     * Update the capability states of the editor.
     *
     * Some of the can* properties will change to reflect the various
     * actions that can be performed with the editor.
     */
    _updateState() {
        const canEdit = this.get('canEdit');
        const editing = this.get('editing');
        const comment = this.get('comment');

        this.set({
            canDelete: canEdit && editing && comment && !comment.isNew(),
            canSave: canEdit && editing && this.get('text') !== '',
        });
    },
}, RB.ExtraDataMixin));
