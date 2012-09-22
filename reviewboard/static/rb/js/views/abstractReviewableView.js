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
    initialize: function() {
        console.assert(this.commentBlockView,
                       'commentBlockView must be defined by the subclass');
        console.assert(this.commentsListName,
                       'commentsListName must be defined by the subclass');

        this.commentDlg = gCommentDlg;
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
        /* As soon as we add the comment block, show the dialog. */
        this.once('commentBlockViewAdded', function(commentBlockView) {
            this.showCommentDlg(commentBlockView);
        }, this);

        this.model.commentBlocks.add(opts);
    },

    /*
     * Shows the comment details dialog for a comment block.
     */
    showCommentDlg: function(commentBlockView) {
        this.commentDlg
            .one('close', _.bind(function() {
                var commentBlock = commentBlockView.model;

                commentBlock.ensureDraftComment();

                this.commentDlg
                    .setDraftComment(commentBlock.get('draftComment'))
                    .setCommentsList(commentBlock.get('serializedComments'),
                                     this.commentsListName);
                commentBlockView.positionCommentDlg(this.commentDlg);
                this.commentDlg.open();
            }, this))
            .close();
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
