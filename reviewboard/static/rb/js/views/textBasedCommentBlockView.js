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
    events: {
        'click': '_onClicked',
        'mouseover': '_onMouseOver',
        'mouseleave': '_onMouseLeave'
    },

    tagName: 'span',
    className: 'commentflag',
    timeoutId: 'textBasedCommentBlockTimeoutId',

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
        _super(this).tooltipSides = 'rlbt';

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
        this.$el.html(this.template(_.defaults(this.model.attributes, {
            anchorName: this.buildAnchorName()
        })));

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
        /*
         * This can't use _.super() because AbstractCommentBlockView doesn't
         * define a 'remove'.
         */
        Backbone.View.prototype.remove.call(this);

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
     * Builds the name for the comment flag anchor.
     */
    buildAnchorName: function() {
        return 'line' + this.model.get('beginLineNum');
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
    },

    /*
     * Handler for when the comment block is clicked.
     *
     * Emits the 'clicked' signal so that parent views can process it.
     */
    _onClicked: function() {
       this.trigger('clicked');
    },

    /*
     * Handler for mouseover event.
     *
     * Spreads out the comment bubbles if they are overlapping.
     */
    _onMouseOver: function() {
        var $parent = this.$el.parent(),
            commentBubbles = $parent.find('.commentflag'),
            initialWidth = this.$el.find('.commentflag-inner').width(),
            initialLeft = commentBubbles.first().position().left,
            spreadDistance = initialWidth + 3, /* Pixels between bubbles */
            timeoutId = $parent.data(this.timeoutId);

        clearTimeout(timeoutId);

        /*
         * timeoutId will only be defined during a mouseleave event, where the
         * comment bubbles are spread out. It will be undefined when the
         * comment bubbles are collapsed to the side.
         *
         * TODO: Take into account bubbles that overlap but do not start on
         *       the same row.
         */
        if (commentBubbles.length !== 1 && typeof timeoutId === 'undefined') {
            commentBubbles.each(_.bind(function(index, bubble) {
                var leftMargin = initialLeft + spreadDistance * index,
                    width = initialWidth + spreadDistance *
                            (commentBubbles.length - index - 1);

                this._shiftBubble(bubble, width, leftMargin);
            }, this));
        }
    },

    /*
     * Handler for mouseleave event.
     *
     * Collapse comment bubbles to the side if the mouse is not hovering over
     * them.
     */
    _onMouseLeave: function() {
        var $parent = this.$el.parent(),
            commentBubbles = $parent.find('.commentflag'),
            initialWidth = this.$el.find('.commentflag-inner').width(),
            initialLeft = commentBubbles.first().position().left;

        /*
         * Stores timeoutId to clear the timeout event if mouse is still
         * hovering over the range of overlapping bubbles.
         */
        $parent.data(this.timeoutId, setTimeout(_.bind(function() {
            if (commentBubbles.length !== 1) {
                commentBubbles.each(_.bind(function(index, bubble) {
                    this._shiftBubble(bubble, initialWidth, initialLeft);
                }, this));
            }

            /*
             * Remove timeoutId data to represent that the range of
             * overlapping bubbles are no longer spread out.
             */
            $parent.removeData(this.timeoutId)
        }, this), 500));
    },

    /*
     * Animates the expansion and collapse of the the overlapping comment
     * bubbles.
     */
    _shiftBubble: function(bubble, width, left) {
        $(bubble)
            .css('width', width + 'px')
            .stop()
            .animate({
                'left': left + 'px'
            }, 500);
    }
});
