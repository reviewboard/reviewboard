/*
 * Displays a review UI for screenshots.
 *
 * This will display all existing comments on a screenshot as selection
 * boxes, and gives users the ability to click and drag across part of the
 * screenshot to leave a comment on that area.
 */
RB.ScreenshotReviewableView = RB.AbstractReviewableView.extend({
    className: 'screenshot-review-ui',

    commentBlockView: RB.ScreenshotCommentBlockView,
    commentsListName: 'screenshot_comments',

    events: {
        'mousedown .selection-container': '_onMouseDown',
        'mouseup .selection-container': '_onMouseUp',
        'mousemove .selection-container': '_onMouseMove'
    },

    /*
     * Initializes the view.
     */
    initialize: function() {
        RB.AbstractReviewableView.prototype.initialize.call(this);

        _.bindAll(this, '_adjustPos');

        this._activeSelection = {};

        /*
         * Add any CommentBlockViews to the selection area when they're
         * created.
         */
        this.on('commentBlockViewAdded', function(commentBlockView) {
            this._$selectionArea.append(commentBlockView.$el);
        }, this);
    },

    /*
     * Renders the view.
     *
     * This will set up a selection area over the image and create a
     * selection rectangle that will be shown when dragging.
     *
     * Any time the window resizes, the comment positions will be adjusted.
     */
    renderContent: function() {
        var self = this;

        this._$image = $('<img/>')
            .attr({
                caption: this.model.get('caption'),
                src: this.model.get('imageURL')
            });

        this._$selectionArea = $('<div/>')
            .addClass('selection-container')
            .proxyTouchEvents();

        this._$selectionRect = $('<div/>')
            .addClass('selection-rect')
            .prependTo(this._$selectionArea)
            .proxyTouchEvents()
            .hide();

        this.$el
            /*
             * Register a hover event to hide the comments when the mouse
             * is not over the comment area.
             */
            .hover(
                function() {
                    self._$selectionArea.show();
                },
                function() {
                    if (self._$selectionRect.is(':hidden') &&
                        self.commentDlg.is(':hidden')) {
                        self._$selectionArea.hide();
                    }
                })
            .append(this._$selectionArea)
            .append(this._$image);

        /*
         * Reposition the selection area on page resize or loaded, so that
         * comments are in the right locations.
         */
        $(window)
            .resize(this._adjustPos)
            .load(this._adjustPos);

        return this;
    },

    /*
     * Handles a mousedown on the selection area.
     *
     * If this is the first mouse button, and it's not being placed on
     * an existing comment block, then this will begin the creation of a new
     * comment block starting at the mousedown coordinates.
     */
    _onMouseDown: function(evt) {
        if (evt.which === 1 &&
            this.commentDlg.is(':hidden') &&
            !$(evt.target).hasClass('selection-flag')) {
            var offset = this._$selectionArea.offset();

            this._activeSelection.beginX =
                evt.pageX - Math.floor(offset.left) - 1;
            this._activeSelection.beginY =
                evt.pageY - Math.floor(offset.top) - 1;

            this._$selectionRect
                .move(this._activeSelection.beginX,
                      this._activeSelection.beginY)
                .width(1)
                .height(1)
                .show();

            if (this._$selectionRect.is(':hidden')) {
                this.commentDlg.hide();
            }

            return false;
        }
    },

    /*
     * Handles a mouseup on the selection area.
     *
     * This will finalize the creation of a comment block and pop up the
     * comment dialog.
     */
    _onMouseUp: function(evt) {
        if (this.commentDlg.is(':hidden') &&
            this._$selectionRect.is(":visible")) {
            var width = this._$selectionRect.width(),
                height = this._$selectionRect.height(),
                offset = this._$selectionRect.position();

            evt.stopPropagation();
            this._$selectionRect.hide();

            /*
             * If we don't pass an arbitrary minimum size threshold,
             * don't do anything. This helps avoid making people mad
             * if they accidentally click on the image.
             */
            if (width > 5 && height > 5) {
                this.createAndEditCommentBlock({
                    screenshotID: this.model.get('screenshotID'),
                    x: Math.floor(offset.left),
                    y: Math.floor(offset.top),
                    width: width,
                    height: height
                });
            }
        }
    },

    /*
     * Handles a mousemove on the selection area.
     *
     * If we're creating a comment block, this will update the
     * size/position of the block.
     */
    _onMouseMove: function(evt) {
        if (this.commentDlg.is(':hidden') &&
            this._$selectionRect.is(":visible")) {
            var offset = this._$selectionArea.offset(),
                x = evt.pageX - Math.floor(offset.left) - 1,
                y = evt.pageY - Math.floor(offset.top) - 1;

            this._$selectionRect
                .css(this._activeSelection.beginX <= x
                     ? {
                           left:  this._activeSelection.beginX,
                           width: x - this._activeSelection.beginX
                       }
                     : {
                           left:  x,
                           width: this._activeSelection.beginX - x
                       })
                .css(this._activeSelection.beginY <= y
                     ? {
                           top:    this._activeSelection.beginY,
                           height: y - this._activeSelection.beginY
                       }
                     : {
                           top:    y,
                           height: this._activeSelection.beginY - y
                       });

            return false;
        }
    },

    /*
     * Reposition the selection area to the right locations.
     */
    _adjustPos: function() {
        var offset = this._$image.position();

        /*
         * The margin: 0 auto means that position.left() will return
         * the left-most part of the entire block, rather than the actual
         * position of the image on Chrome. Every other browser returns 0
         * for this margin, as we'd expect. So, just play it safe and
         * offset by the margin-left. (Bug #1050)
         */
        offset.left += this._$image.getExtents("m", "l");

        if ($.browser.msie && $.browser.version === 6) {
            offset.left -= self.getExtents("mp", "l");
        }

        this._$selectionArea
            .width(this._$image.width())
            .height(this._$image.height())
            .css("left", offset.left);
    }
});
