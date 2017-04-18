/*
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

    template: _.template([
        '<span class="commentflag-shadow"></span>',
        '<span class="commentflag-inner">',
        ' <span class="commentflag-count"></span>',
        '</span>',
        '<a name="<%= anchorName %>" class="commentflag-anchor"></a>'
    ].join('')),

    /*
     * Initializes the view.
     */
    initialize: function() {
        this.$beginRow = null;
        this.$endRow = null;
        this._$window = $(window);

        this._prevCommentHeight = null;
        this._prevWindowWidth = null;
        this._resizeRegistered = false;
    },

    /*
     * Renders the contents of the comment flag.
     *
     * This will display the comment flag and then start listening for
     * events for updating the comment count or repositioning the comment
     * (for zoom level changes and wrapping changes).
     */
    renderContent: function() {
        this.$el.html(this.template(_.defaults(this.model.attributes, {
            anchorName: this.buildAnchorName()
        })));

        this.$('.commentflag-count')
            .bindProperty('text', this.model, 'count', {
                elementToModel: false
            });
    },

    /*
     * Removes the comment from the page.
     */
    remove: function() {
        /*
         * This can't use _.super() because AbstractCommentBlockView doesn't
         * define a 'remove'.
         */
        Backbone.View.prototype.remove.call(this);

        if (this._resizeRegistered) {
            this._$window.off('resize.' + this.cid);
        }
    },

    /*
     * Sets the row span for the comment flag.
     *
     * The comment will update to match the row of lines.
     */
    setRows: function($beginRow, $endRow) {
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

    /*
     * Positions the comment dialog relative to the comment flag position.
     *
     * The dialog will be positioned in the center of the page (horizontally),
     * just to the bottom of the flag.
     */
    positionCommentDlg: function(commentDlg) {
        commentDlg.$el.css({
            left: $(document).scrollLeft() +
                  (this._$window.width() - commentDlg.$el.width()) / 2,
            top: this.$endRow.offset().top + this.$endRow.height()
        });
    },

    /*
     * Positions the comment update notifications bubble.
     *
     * The bubble will be positioned just to the top-right of the flag.
     */
    positionNotifyBubble: function($bubble) {
        $bubble.css({
            left: this.$el.width(),
            top: 0
        });
    },

    /*
     * Builds the name for the comment flag anchor.
     */
    buildAnchorName: function() {
        return 'line' + this.model.get('beginLineNum');
    },

    /*
     * Updates the size of the comment flag.
     */
    _updateSize: function() {
        var windowWidth = this._$window.width(),
            commentHeight;

        if (this._prevWindowWidth === windowWidth) {
            return;
        }

        this._prevWindowWidth = windowWidth;

        /*
         * On IE and Safari, the marginTop in getExtents may be wrong.
         * We force a value that ends up working for us.
         */
        commentHeight = this.$endRow.offset().top +
                        this.$endRow.outerHeight() -
                        this.$beginRow.offset().top -
                        (this.$el.getExtents('m', 't') || -4);

        if (commentHeight !== this._prevCommentHeight) {
            this.$el.height(commentHeight);
            this._prevCommentHeight = commentHeight;
        }
    }
});
