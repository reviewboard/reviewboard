/*
 * Abstract base for review UIs.
 *
 * This provides all the basics for creating a review UI. It does the
 * work of loading in comments, creating views, and displaying comment dialogs,
 */
RB.AbstractReviewableView = Backbone.View.extend({
    /*
     * The AbstractCommentBlockView subclass that will be instantiated for
     * rendering comment blocks.
     */
    commentBlockView: null,

    /* The list type (as a string) for passing to CommentDlg. */
    commentsListName: null,

    /*
     * Initializes AbstractReviewableView.
     */
    initialize: function(options) {
        options = options || {};

        console.assert(this.commentBlockView,
                       'commentBlockView must be defined by the subclass');
        console.assert(this.commentsListName,
                       'commentsListName must be defined by the subclass');

        this.commentDlg = null;
        this._activeCommentBlock = null;
        this.renderedInline = options.renderedInline || false;
    },

    /*
     * Renders the reviewable to the page.
     *
     * This will call the subclass's renderContent(), and then handle
     * rendering each comment block on the reviewable.
     */
    render: function() {
        this.renderContent();

        this.model.commentBlocks.each(this._addCommentBlockView, this);
        this.model.commentBlocks.on('add', this._addCommentBlockView, this);

        return this;
    },

    /*
     * Renders the content of the reviewable.
     *
     * This should be overridden by subclasses.
     */
    renderContent: function() {
    },

    /*
     * Creates a new comment in a comment block and opens it for editing.
     */
    createAndEditCommentBlock: function(opts) {
        var defaultCommentBlockFields =
            _.result(this.model, 'defaultCommentBlockFields');

        if (defaultCommentBlockFields.length === 0 &&
            this.model.reviewableIDField) {
            console.log('Deprecation notice: Reviewable subclass is missing ' +
                        'defaultCommentBlockFields. Rename reviewableIDField ' +
                        'to defaultCommentBlockFields, and make it a list.');
            defaultCommentBlockFields = [this.model.reviewableIDField];
        }

        /* As soon as we add the comment block, show the dialog. */
        this.once('commentBlockViewAdded', function(commentBlockView) {
            this.showCommentDlg(commentBlockView);
        }, this);

        _.extend(opts,
                 _.pick(this.model.attributes, defaultCommentBlockFields));
        this.model.createCommentBlock(opts);
    },

    /*
     * Shows the comment details dialog for a comment block.
     */
    showCommentDlg: function(commentBlockView) {
        var commentBlock = commentBlockView.model;

        commentBlock.ensureDraftComment();

        if (this._activeCommentBlock === commentBlock) {
            return;
        }

        this.stopListening(this.commentDlg, 'closed');
        this.commentDlg = RB.CommentDialogView.create({
            comment: commentBlock.get('draftComment'),
            publishedComments: commentBlock.get('serializedComments'),
            publishedCommentsType: this.commentsListName,
            position: function(dlg) {
                commentBlockView.positionCommentDlg(dlg);
            }
        });
        this._activeCommentBlock = commentBlock;

        this.listenTo(this.commentDlg, 'closed', function() {
            this.commentDlg = null;
            this._activeCommentBlock = null;
        });
    },

    /*
     * Adds a CommentBlockView for the given CommentBlock.
     *
     * This will create a view for the block, render it, listen for clicks
     * in order to show the comment dialog, and then emit
     * 'commentBlockViewAdded'.
     */
    _addCommentBlockView: function(commentBlock) {
        var commentBlockView = new this.commentBlockView({
            model: commentBlock
        });

        commentBlockView.on('clicked', function() {
            this.showCommentDlg(commentBlockView);
        }, this);

        commentBlockView.render();
        this.trigger('commentBlockViewAdded', commentBlockView);
    }
});
