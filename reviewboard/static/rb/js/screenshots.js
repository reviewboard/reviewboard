/*
 * Creates a box for creating and seeing all comments on a screenshot.
 *
 * @param {object} regions  The regions containing comments.
 *
 * @return {jQuery} This jQuery.
 */
jQuery.fn.screenshotCommentBox = function(regions) {
    var self = this;

    /* State */
    var activeCommentBlock = null;

    /* Page elements */
    var image = $("img", this);

    var selectionArea =
        $('<div id="selection-container"/>')
        .prependTo(this);

    var activeSelection =
        $('<div id="selection-interactive"/>')
        .prependTo(selectionArea)
        .hide();

    gCommentDlg.on("close", function() { activeCommentBlock = null; });

    /*
     * Register events on the selection area for handling new comment
     * creation.
     */
    $([image[0], selectionArea[0]])
        .mousedown(function(evt) {
            if (evt.which == 1 && !activeCommentBlock &&
                !$(evt.target).hasClass("selection-flag")) {
                var offset = selectionArea.offset();
                activeSelection.beginX =
                    evt.pageX - Math.floor(offset.left) - 1;
                activeSelection.beginY =
                    evt.pageY - Math.floor(offset.top) - 1;

                activeSelection
                    .move(activeSelection.beginX, activeSelection.beginY)
                    .width(1)
                    .height(1)
                    .show();

                if (activeSelection.is(":hidden")) {
                    gCommentDlg.hide();
                }

                return false;
            }
        })
        .mouseup(function(evt) {
            if (!activeCommentBlock && activeSelection.is(":visible")) {
                evt.stopPropagation();

                var width  = activeSelection.width();
                var height = activeSelection.height();
                var offset = activeSelection.position();

                activeSelection.hide();

                /*
                 * If we don't pass an arbitrary minimum size threshold,
                 * don't do anything.  This helps avoid making people mad
                 * if they accidentally click on the image.
                 */
                if (width > 5 && height > 5) {
                    if (!activeCommentBlock) {
                        showCommentDlg(addCommentBlock(Math.floor(offset.left),
                                                       Math.floor(offset.top),
                                                       width, height));
                    } else {
                        // TODO: Reposition the old block. */
                    }
                }
            }
        })
        .mousemove(function(evt) {
            if (!activeCommentBlock && activeSelection.is(":visible")) {
                var offset = selectionArea.offset();
                var x = evt.pageX - Math.floor(offset.left) - 1;
                var y = evt.pageY - Math.floor(offset.top) - 1;

                activeSelection
                    .css(activeSelection.beginX <= x
                         ? {
                               left:  activeSelection.beginX,
                               width: x - activeSelection.beginX
                           }
                         : {
                               left:  x,
                               width: activeSelection.beginX - x
                           })
                    .css(activeSelection.beginY <= y
                         ? {
                               top:    activeSelection.beginY,
                               height: y - activeSelection.beginY
                           }
                         : {
                               top:    y,
                               height: activeSelection.beginY - y
                           });

                return false;
            }
        })
        .proxyTouchEvents();

    /*
     * Register a hover event to hide the comments when the mouse is not
     * over the comment area.
     */
    this.hover(
        function() {
            selectionArea.show();
        },
        function() {
            if (activeSelection.is(":hidden") &&
                gCommentDlg.is(":hidden")) {
                selectionArea.hide();
            }
        }
    );

    /*
     * Reposition the selection area on page resize or loaded, so that
     * comments are in the right locations.
     */
    $(window)
        .resize(adjustPos)
        .load(adjustPos);

    /* Add all existing comment regions to the page. */
    for (region in regions) {
        var comments = regions[region];
        addCommentBlock(comments[0].x, comments[0].y,
                        comments[0].w, comments[0].h,
                        comments);
    }

    /*
     * Adds a new comment block to the selection area. This may contain
     * existing comments or may be a newly created comment block.
     *
     * @param {int}   x         The X area of the block.
     * @param {int}   y         The Y area of the block.
     * @param {int}   width     The block's width.
     * @param {int}   height    The block's height.
     * @param {array} comments  The list of comments in this block.
     *
     * @return {CommentBlock} The new comment block.
     */
    function addCommentBlock(x, y, width, height, comments) {
        var commentBlock = new RB.ScreenshotCommentBlock({
                screenshotID: gScreenshotId,
                x: x,
                y: y,
                width: width,
                height: height,
                serializedComments: comments || []
            }),
            commentBlockView = new RB.ScreenshotCommentBlockView({
                model: commentBlock
            });

        commentBlockView.on('clicked', function() {
            showCommentDlg(commentBlockView);
        });

        selectionArea.append(commentBlockView.$el);
        commentBlockView.render();

        return commentBlockView;
    }

    /*
     * Shows the comment details dialog for a comment block.
     *
     * @param {CommentBlock} commentBlockView  The comment block view to show.
     */
    function showCommentDlg(commentBlockView) {
        gCommentDlg
            .one("close", function() {
                var commentBlock = commentBlockView.model;

                commentBlock.ensureDraftComment();
                activeCommentBlock = commentBlock;

                gCommentDlg
                    .setDraftComment(commentBlock.get('draftComment'))
                    .setCommentsList(commentBlock.get('serializedComments'),
                                     "screenshot_comments")
                    // XXX
                    .positionToSide(commentBlockView._$flag, {
                        side: 'b',
                        fitOnScreen: true
                    });
                gCommentDlg.open();
            })
            .close();
    }

    /*
     * Reposition the selection area to the right locations.
     */
    function adjustPos() {
        var offset = image.position();

        /*
         * The margin: 0 auto means that position.left() will return
         * the left-most part of the entire block, rather than the actual
         * position of the image on Chrome. Every other browser returns 0
         * for this margin, as we'd expect. So, just play it safe and
         * offset by the margin-left. (Bug #1050)
         */
        offset.left += image.getExtents("m", "l");

        if ($.browser.msie && $.browser.version == 6) {
            offset.left -= self.getExtents("mp", "l");
        }

        selectionArea
            .width(image.width())
            .height(image.height())
            .css("left", offset.left);
    }

    return this;
}

// vim: set et ts=4:
