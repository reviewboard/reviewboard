/**
 * Abstract base for review UIs.
 *
 * This provides all the basics for creating a review UI. It does the
 * work of loading in comments, creating views, and displaying comment dialogs,
 */
RB.AbstractReviewableView = Backbone.View.extend({
    /**
     * The AbstractCommentBlockView subclass.
     *
     * This is the type that will be instantiated for rendering comment blocks.
     */
    commentBlockView: null,

    /**
     * The list type (as a string) for passing to CommentDlg.
     */
    commentsListName: null,

    /**
     * Initialize AbstractReviewableView.
     *
     * Args:
     *     options (object, optional):
     *         Options for the view.
     */
    initialize(options={}) {
        console.assert(this.commentBlockView,
                       'commentBlockView must be defined by the subclass');
        console.assert(this.commentsListName,
                       'commentsListName must be defined by the subclass');

        this.commentDlg = null;
        this._activeCommentBlock = null;
        this.renderedInline = options.renderedInline || false;
    },

    /**
     * Render the reviewable to the page.
     *
     * This will call the subclass's renderContent(), and then handle
     * rendering each comment block on the reviewable.
     *
     * Returns:
     *     RB.AbstractReviewableView:
     *     This object, for chaining.
     */
    render() {
        this.renderContent();

        this.model.commentBlocks.each(this._addCommentBlockView, this);
        this.model.commentBlocks.on('add', this._addCommentBlockView, this);

        return this;
    },

    /**
     * Render the content of the reviewable.
     *
     * This should be overridden by subclasses.
     */
    renderContent() {
    },

    /**
     * Create a new comment in a comment block and opens it for editing.
     *
     * Args:
     *     options (object):
     *         Options for the comment block creation.
     */
    createAndEditCommentBlock(options) {
        if (this.commentDlg !== null &&
            this.commentDlg.model.get('dirty') &&
            !confirm(gettext('You are currently editing another comment. Would you like to discard it and create a new one?'))) {
            return;
        }

        let defaultCommentBlockFields =
            _.result(this.model, 'defaultCommentBlockFields');

        if (defaultCommentBlockFields.length === 0 &&
            this.model.reviewableIDField) {
            console.log('Deprecation notice: Reviewable subclass is missing ' +
                        'defaultCommentBlockFields. Rename reviewableIDField ' +
                        'to defaultCommentBlockFields, and make it a list.');
            defaultCommentBlockFields = [this.model.reviewableIDField];
        }

        /* As soon as we add the comment block, show the dialog. */
        this.once('commentBlockViewAdded',
                  commentBlockView => this.showCommentDlg(commentBlockView));

        _.extend(options,
                 _.pick(this.model.attributes, defaultCommentBlockFields));
        this.model.createCommentBlock(options);
    },

    /**
     * Show the comment details dialog for a comment block.
     *
     * Args:
     *     commentBlockView (RB.AbstractCommentBlockView):
     *         The comment block to show the dialog for.
     */
    showCommentDlg(commentBlockView) {
        const commentBlock = commentBlockView.model;

        commentBlock.ensureDraftComment();

        if (this._activeCommentBlock === commentBlock) {
            return;
        }

        this.stopListening(this.commentDlg, 'closed');
        this.commentDlg = RB.CommentDialogView.create({
            comment: commentBlock.get('draftComment'),
            publishedComments: commentBlock.get('serializedComments'),
            publishedCommentsType: this.commentsListName,
            position: dlg => commentBlockView.positionCommentDlg(dlg),
        });
        this._activeCommentBlock = commentBlock;

        this.listenTo(this.commentDlg, 'closed', () => {
            this.commentDlg = null;
            this._activeCommentBlock = null;
        });
    },

    /**
     * Add a CommentBlockView for the given CommentBlock.
     *
     * This will create a view for the block, render it, listen for clicks
     * in order to show the comment dialog, and then emit
     * 'commentBlockViewAdded'.
     *
     * Args:
     *     commentBlock (RB.AbstractCommentBlock):
     *         The comment block to add a view for.
     */
    _addCommentBlockView(commentBlock) {
        const commentBlockView = new this.commentBlockView({
            model: commentBlock
        });

        commentBlockView.on('clicked', () => this.showCommentDlg(commentBlockView));
        commentBlockView.render();
        this.trigger('commentBlockViewAdded', commentBlockView);
    },
});
