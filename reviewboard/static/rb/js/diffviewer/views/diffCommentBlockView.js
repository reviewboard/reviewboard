/*
 * Displays the comment flag for a comment in the diff viewer.
 *
 * The comment flag handles all interaction for creating/viewing
 * comments, and will update according to any comment state changes.
 */
RB.DiffCommentBlockView = RB.AbstractCommentBlockView.extend({
    tagName: 'span',
    className: 'commentflag',

    tooltipSides: 'rb',

    template: _.template([
        '<span class="commentflag-shadow"></span>',
        '<span class="commentflag-inner">',
        ' <span class="commentflag-count"></span>',
        '</span>',
        '<a name="file<%= fileDiffID %>line<%= beginLineNum %>"',
        '   class="commentflag-anchor">',
        '</a>'
    ].join('')),

    /*
     * Initializes the view.
     */
    initialize: function() {
        this.$beginRow = null;
        this.$endRow = null;

        _.bindAll(this, '_updateSize');
    },

    /*
     * Renders the contents of the comment flag.
     *
     * This will display the comment flag and then start listening for
     * events for updating the comment count or repositioning the comment
     * (for zoom level changes and wrapping changes).
     */
    renderContent: function() {
        this.$el.html(this.template(this.model.attributes));

        this.$('.commentflag-count')
            .bindProperty('text', this.model, 'count', {
                elementToModel: false
            });

        $(window).on('resize', this._updateSize);
    },

    /*
     * Removes the comment from the page.
     */
    remove: function() {
        _.super(this).remove.call(this);

        $(window).off('resize', this._updateSize);
    },

    /*
     * Sets the row span for the comment flag.
     *
     * The comment will update to match the row of lines.
     */
    setRows: function($beginRow, $endRow) {
        this.$beginRow = $beginRow;
        this.$endRow = $endRow;

        this._updateSize();
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
                  ($(window).width() - commentDlg.$el.width()) / 2,
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
     * Updates the size of the comment flag.
     */
    _updateSize: function() {
        if (this.$beginRow && this.$endRow) {
            /*
             * On IE and Safari, the marginTop in getExtents may be wrong.
             * We force a value that ends up working for us.
             */
            this.$el.height(this.$endRow.offset().top +
                            this.$endRow.outerHeight() -
                            this.$beginRow.offset().top -
                            (this.$el.getExtents('m', 't') || -4));
        }
    }
});
