/**
 * Provides a visual comment indicator to display comments for text-based file
 * attachments.
 *
 * This will show a comment indicator flag (a "ghost comment flag") beside the
 * content indicating there are comments there. It will also show the
 * number of comments, along with a tooltip showing comment summaries.
 *
 * This is meant to be used with a TextCommentBlock model.
 */
RB.TextBasedCommentBlockView = RB.AbstractCommentBlockView.extend({
    tagName: 'span',
    className: 'commentflag',

    template: _.template(dedent`
        <span class="commentflag-shadow"></span>
        <span class="commentflag-inner">
         <span class="commentflag-count"></span>
        </span>
        <a name="<%= anchorName %>" class="commentflag-anchor"></a>
    `),

    /**
     * Initialize the view.
     */
    initialize() {
        this.$beginRow = null;
        this.$endRow = null;
        this._$window = $(window);

        this._prevCommentHeight = null;
        this._prevWindowWidth = null;
        this._resizeRegistered = false;
    },

    /**
     * Render the contents of the comment flag.
     *
     * This will display the comment flag and then start listening for
     * events for updating the comment count or repositioning the comment
     * (for zoom level changes and wrapping changes).
     *
     * Returns:
     *     RB.TextBasedCommentBlockView:
     *     This object, for chaining.
     */
    renderContent() {
        this.$el.html(this.template(_.defaults(this.model.attributes, {
            anchorName: this.buildAnchorName(),
        })));

        this.$('.commentflag-count')
            .bindProperty('text', this.model, 'count', {
                elementToModel: false,
            });
    },

    /**
     * Remove the comment from the page.
     */
    remove() {
        /*
         * This can't use _.super() because AbstractCommentBlockView doesn't
         * define a 'remove'.
         */
        Backbone.View.prototype.remove.call(this);

        if (this._resizeRegistered) {
            this._$window.off('resize.' + this.cid);
        }
    },

    /**
     * Set the row span for the comment flag.
     *
     * The comment will update to match the row of lines.
     *
     * Args:
     *     $beginRow (jQuery):
     *         The first row of the comment.
     *
     *     $endRow (jQuery):
     *         The last row of the comment. This may be the same as
     *         ``$beginRow``.
     */
    setRows($beginRow, $endRow) {
        this.$beginRow = $beginRow;
        this.$endRow = $endRow;

        /*
         * We need to set the sizes and show the element after other layout
         * operations and the DOM have settled.
         */
        _.defer(_.bind(function() {
            this._updateSize();
            this.$el.show();
        }, this));

        if ($beginRow && $endRow) {
            if (!this._resizeRegistered) {
                this._$window.on('resize.' + this.cid,
                                 _.bind(this._updateSize, this));
            }
        } else {
            if (this._resizeRegistered) {
                this._$window.off('resize.' + this.cid);
            }
        }
    },

    /**
     * Position the comment dialog relative to the comment flag position.
     *
     * The dialog will be positioned in the center of the page (horizontally),
     * just to the bottom of the flag.
     *
     * Args:
     *     commntDlg (RB.CommentDialogView):
     *          The view for the comment dialog.
     */
    positionCommentDlg(commentDlg) {
        commentDlg.$el.css({
            left: $(document).scrollLeft() +
                  (this._$window.width() - commentDlg.$el.width()) / 2,
            top: this.$endRow.offset().top + this.$endRow.height(),
        });
    },

    /**
     * Position the comment update notifications bubble.
     *
     * The bubble will be positioned just to the top-right of the flag.
     *
     * Args:
     *     $bubble (jQuery):
     *         The selector for the notification bubble.
     */
    positionNotifyBubble($bubble) {
        $bubble.css({
            left: this.$el.width(),
            top: 0,
        });
    },

    /**
     * Return the name for the comment flag anchor.
     *
     * Returns:
     *     string:
     *     The name to use for the anchor element.
     */
    buildAnchorName() {
        return `line${this.model.get('beginLineNum')}`;
    },

    /**
     * Update the size of the comment flag.
     */
    _updateSize() {
        const windowWidth = this._$window.width();

        if (this._prevWindowWidth === windowWidth) {
            return;
        }

        this._prevWindowWidth = windowWidth;

        /*
         * On IE and Safari, the marginTop in getExtents may be wrong.
         * We force a value that ends up working for us.
         */
        const commentHeight = this.$endRow.offset().top +
                              this.$endRow.outerHeight() -
                              this.$beginRow.offset().top -
                              (this.$el.getExtents('m', 't') || -4);

        if (commentHeight !== this._prevCommentHeight) {
            this.$el.height(commentHeight);
            this._prevCommentHeight = commentHeight;
        }
    },
});
