(function() {


var CommentRowSelector,
    getLineNum;


/*
 * Returns the line number for a row.
 */
getLineNum = function(row) {
    return parseInt(row.getAttribute('line'), 10);
};


/*
 * Provides multi-line commenting capabilities for a diff.
 *
 * This tacks on commenting capabilities onto a DiffReviewableView's
 * element. It listens for mouse events that begin/end the creation of
 * a new comment.
 */
CommentRowSelector = Backbone.View.extend({
    ghostCommentFlagTemplate: _.template([
        '<span class="commentflag ghost-commentflag">',
        ' <span class="commentflag-shadow"></span>',
        ' <span class="commentflag-inner"></span>',
        '</span>'
    ].join('')),

    events: {
        'mousedown': '_onMouseDown',
        'mouseup': '_onMouseUp',
        'mouseover': '_onMouseOver',
        'mouseout': '_onMouseOut',
        'touchmove': '_onTouchMove',
        'touchcancel': '_onTouchCancel'
    },

    /*
     * Initializes the commenting selector.
     */
    initialize: function() {
        this._$begin = null;
        this._$end = null;
        this._beginLineNum = 0;
        this._endLineNum = 0;
        this._lastSeenIndex = 0;

        this._$ghostCommentFlag = null;
        this._$ghostCommentFlagCell = null;
    },

    /*
     * Removes the selector.
     */
    remove: function() {
        Backbone.View.prototype.remove.call(this);

        this._$ghostCommentFlag.remove();
    },

    /*
     * Renders the selector.
     */
    render: function() {
        this._$ghostCommentFlag = $(this.ghostCommentFlagTemplate())
            .on({
                mousedown: _.bind(this._onMouseDown, this),
                mouseup: _.bind(this._onMouseUp, this),
                mouseover: _.bind(this._onMouseOver, this),
                mouseout: _.bind(this._onMouseOut, this)
            })
            .hide()
            .appendTo('body');

        return this;
    },

    /*
     * Begins the selection of line numbers.
     */
    _begin: function($row) {
        var lineNum = getLineNum($row[0]);

        this._$begin = $row;
        this._$end = $row;
        this._beginLineNum = lineNum;
        this._endLineNum = lineNum;
        this._lastSeenIndex = $row[0].rowIndex;

        $row.addClass('selected');
        this.$el.disableSelection();
    },

    /*
     * Finalizes the selection and pops up a comment dialog.
     */
    _end: function($row) {
        var $commentFlag;

        if (this._beginLineNum === this._endLineNum) {
            /* See if we have a comment flag on the selected row. */
            $commentFlag = $row.find('.commentflag');

            if ($commentFlag.length === 1) {
                $commentFlag.click();
                return;
            }
        }

        /*
         * Selection was finalized. Create the comment block
         * and show the comment dialog.
         */
        this.options.reviewableView.createAndEditCommentBlock({
            beginLineNum: this._beginLineNum,
            endLineNum: this._endLineNum,
            $beginRow: this._$begin,
            $endRow: this._$end
        });
    },

    /*
     * Adds a row to the selection. This will update the selection range
     * and mark the rows as selected.
     *
     * This row is assumed to be the most recently selected row, and
     * will mark the new beginning or end of the selection.
     */
    _addRow: function($row) {
        var lineNum,
            min,
            max,
            i;

        /* We have an active selection. */
        lineNum = getLineNum($row[0]);

        if (lineNum < this._beginLineNum) {
            this._$begin = $row;
            this._beginLineNum = lineNum;
        } else if (lineNum > this._beginLineNum) {
            this._$end = $row;
            this._endLineNum = lineNum;
        }

        min = Math.min(this._lastSeenIndex, $row[0].rowIndex);
        max = Math.max(this._lastSeenIndex, $row[0].rowIndex);

        for (i = min; i <= max; i++) {
            $(this.el.rows[i]).addClass('selected');
        }

        this._lastSeenIndex = $row[0].rowIndex;
    },

    /*
     * Highlights a row.
     *
     * This will highlight a row and show a ghost comment flag. This is done
     * when the mouse hovers over the row.
     */
    _highlightRow: function($row) {
        var $lineNumCell = $($row[0].cells[0]);

        /* See if we have a comment flag in here. */
        if ($lineNumCell.find('.commentflag').length === 0) {
            this._$ghostCommentFlag
                .css('top', $row.offset().top - 1)
                .show()
                .parent()
                    .removeClass('selected');
            this._$ghostCommentFlagCell = $lineNumCell;
        }

        $row.addClass('selected');
    },

    /*
     * Removes any old rows from the selection, based on the most recent
     * row selected.
     */
    _removeOldRows: function($row) {
        var destRowIndex = $row[0].rowIndex;

        if (destRowIndex >= this._$begin[0].rowIndex) {
            if (   this._lastSeenIndex !== this._$end[0].rowIndex
                && this._lastSeenIndex < destRowIndex) {
                /*
                 * We're removing from the top of the range. The beginning
                 * location will need to be moved.
                 */
                this._removeSelectionClasses(this._lastSeenIndex, destRowIndex);
                this._$begin = $row;
                this._beginLineNum = getLineNum($row[0]);
            } else {
                /*
                 * We're removing from the bottom of the selection. The end
                 * location will need to be moved.
                 */
                this._removeSelectionClasses(destRowIndex,
                                             this._lastSeenIndex);

                this._$end = $row;
                this._endLineNum = getLineNum($row[0]);
            }

            this._lastSeenIndex = destRowIndex;
        }
    },

    /*
     * Resets the selection information.
     */
    _reset: function() {
        if (this._$begin) {
            /* Reset the selection. */
            this._removeSelectionClasses(this._$begin[0].rowIndex,
                                         this._$end[0].rowIndex);

            this._$begin = null;
            this._$end = null;
            this._beginLineNum = 0;
            this._endLineNum = 0;
            this._lastSeenIndex = 0;
        }

        this._$ghostCommentFlagCell = null;

        /* Re-enable text selection on IE */
        this.$el.enableSelection();
    },

    /*
     * Removes selection classes on a range of rows.
     */
    _removeSelectionClasses: function(startRowIndex, endRowIndex) {
        var i;

        for (i = startRowIndex; i <= endRowIndex; i++) {
            $(this.el.rows[i]).removeClass('selected');
        }
    },

    /*
     * Returns whether a particular cell is a line number cell.
     */
    _isLineNumCell: function(cell) {
        return cell.tagName === 'TH' &&
               cell.parentNode.getAttribute('line');
    },

    /*
     * Returns the actual cell node in the table.
     *
     * If the node specified is the ghost flag, this will return the
     * cell the ghost flag represents.
     *
     * If this is a comment flag inside a cell, this will return the
     * comment flag's parent cell
     *
     * @return {jQuery} The row.
     */
    _getActualLineNumCell: function($node) {
        if ($node.hasClass('commentflag')) {
            if ($node[0] === this._$ghostCommentFlag[0]) {
                $node = this._$ghostCommentFlagCell;
            } else {
                $node = $node.parent();
            }
        }

        return $node;
    },

    /*
     * Handles the mouse down event, which begins selection for comments.
     */
    _onMouseDown: function(e) {
        var node = e.target;

        if (this._$ghostCommentFlagCell) {
            node = this._$ghostCommentFlagCell[0];
        }

        if (this._isLineNumCell(node)) {
            this._begin($(node.parentNode));
            return false;
        }

        return true;
    },

    /*
     * Handles the mouse up event, which finalizes selection of a range of
     * lines.
     *
     * This will create a new comment block and display the comment dialog.
     */
    _onMouseUp: function(e) {
        var node = e.target;

        e.preventDefault();

        if (this._$ghostCommentFlagCell) {
            node = this._$ghostCommentFlagCell[0];
        }

        if (this._isLineNumCell(node)) {
            this._end(this._getActualLineNumCell($(node)).parent());
            e.stopImmediatePropagation();
        }

        this._reset();
    },

    /*
     * Handles the mouse over event.
     *
     * This will update the selection, if there is one, to include this row
     * in the range, and set the "selected" class on the new row.
     */
    _onMouseOver: function(e) {
        var $node = this._getActualLineNumCell($(e.target)),
            $row = $node.parent();

        if (this._isLineNumCell($node[0])) {
            if (this._$begin) {
                this._addRow($row);
            } else {
                this._highlightRow($row);
            }
        } else if (this._$ghostCommentFlagCell &&
                   $node[0] !== this._$ghostCommentFlagCell[0]) {
            $row.removeClass('selected');
        }
    },

    /*
     * Handles the mouse out event, removing any lines outside the new range
     * from the selection.
     */
    _onMouseOut: function(e) {
        var relTarget = e.relatedTarget,
            $node = this._getActualLineNumCell($(e.target));

        if (relTarget !== this._$ghostCommentFlag[0]) {
            this._$ghostCommentFlag.hide();
            this._$ghostCommentFlagCell = null;
        }

        if (this._$begin) {
            if (relTarget && this._isLineNumCell(relTarget)) {
                this._removeOldRows($(relTarget.parentNode));
            }
        } else if ($node && this._isLineNumCell($node[0])) {
            /*
             * Opera seems to generate lots of spurious mouse-out
             * events, which would cause us to get all sorts of
             * errors in here unless we check the target above.
             */
            $node.parent().removeClass('selected');
        }
    },

    /*
     * Handles touch move events.
     *
     * Simulates mouse clicks/drags for line number selection.
     */
    _onTouchMove: function(e) {
        var firstTouch = e.originalEvent.targetTouches[0],
            target = document.elementFromPoint(firstTouch.pageX,
                                               firstTouch.pageY),
            $node = this._getActualLineNumCell($(target)),
            $row = node.parent();

        if (   this._lastSeenIndex !== $row[0].rowIndex
            && this._isLineNumCell($node[0])) {
            this._removeOldRows($row);
            this._addRow($row);
        }
    },

    /*
     * Handles touch cancel events.
     *
     * Resets the line number selection.
     */
    _onTouchCancel: function() {
        this._reset();
    }
});


/*
 * Handles reviews of the diff for a file.
 *
 * This provides commenting abilities for ranges of lines on a diff, as well
 * as showing existing comments, and handling other interaction around
 * per-file diffs.
 */
RB.DiffReviewableView = RB.AbstractReviewableView.extend({
    tagName: 'table',

    commentBlockView: RB.DiffCommentBlockView,
    commentsListName: 'diff_comments',

    events: {
        'click thead tr': '_onFileHeaderClicked',
        'click .moved-to, .moved-from': '_onMovedLineClicked',
        'click .diff-collapse-btn': '_onCollapseChunkClicked',
        'click .diff-expand-btn': '_onExpandChunkClicked',
        'mouseup': '_onMouseUp'
    },

    /*
     * Initializes the reviewable for a file's diff.
     */
    initialize: function() {
        _.super(this).initialize.call(this);

        _.bindAll(this, '_updateCollapseButtonPos');

        this._selector = new CommentRowSelector({
            el: this.el,
            reviewableView: this
        });

        this._hiddenCommentBlockViews = [];
        this._visibleCommentBlockViews = [];
        this._$collapseButtons = $();

        /*
         * Wrap this only once so we don't have to re-wrap every time
         * the page scrolls.
         */
        this._$window = $(window);

        this.on('commentBlockViewAdded', this._placeCommentBlockView, this);
    },

    /*
     * Removes the reviewable from the DOM.
     */
    remove: function() {
        RB.AbstractReviewableView.prototype.remove.call(this);

        this._$window.off('scroll resize', this._updateCollapseButtonPos);

        this._selector.remove();
    },

    /*
     * Renders the reviewable.
     */
    render: function() {
        _.super(this).render.call(this);

        this._selector.render();

        _.each(this.$el.children('tbody.binary'), function(thumbnailEl) {
            var $thumbnail = $(thumbnailEl),
                id = $thumbnail.data('file-id'),
                $caption = $thumbnail.find('.file-caption .edit'),
                reviewRequest = this.model.get('reviewRequest'),
                fileAttachment = reviewRequest.createFileAttachment({
                    id: id
                });

            if (!$caption.hasClass('empty-caption')) {
                fileAttachment.set('caption', $caption.text());
            }
        }, this);

        this._$window.on('scroll resize', this._updateCollapseButtonPos);

        return this;
    },

    /*
     * Toggles the display of whitespace-only chunks.
     */
    toggleWhitespaceOnlyChunks: function() {
        this.$('tbody tr.whitespace-line').toggleClass('dimmed');

        _.each(this.$el.children('tbody.whitespace-chunk'), function(chunk) {
            var $chunk = $(chunk),
                dimming = $chunk.hasClass('replace'),
                chunkID = chunk.id.split('chunk')[1],
                $children = $chunk.children();

            $chunk.toggleClass('replace');

            $($children[0]).toggleClass('first');
            $($children[$children.length - 1]).toggleClass('last');

            if (dimming) {
                this.trigger('chunkDimmed', chunkID);
            } else {
                this.trigger('chunkUndimmed', chunkID);
            }
        }, this);

        /*
         * Swaps the visibility of the "This file has whitespace changes"
         * tbody and the chunk siblings.
         */
        this.$el.children('tbody.whitespace-file')
            .siblings('tbody')
            .addBack()
                .toggle();
    },

    /*
     * Finds the row in a table matching the specified line number.
     *
     * This will perform a binary search of the lines trying to find
     * the matching line number. It will then return the row element,
     * if found.
     */
    _findLineNumRow: function(lineNum, startRow, endRow) {
        var row = null,
            table = this.el,
            rowOffset = 1, // Get past the headers.
            guessRowNum,
            guessRow,
            oldHigh,
            oldLow,
            high,
            low,
            value,
            found,
            i,
            j;

        if (table.rows.length - rowOffset > lineNum) {
            row = table.rows[rowOffset + lineNum];

            // Account for the "x lines hidden" row.
            if (row && getLineNum(row) === lineNum) {
                return row;
            }
        }

        if (startRow) {
            // startRow already includes the offset, so we need to remove it.
            startRow -= rowOffset;
        }

        low = startRow || 1;
        high = Math.min(endRow || table.rows.length, table.rows.length);

        if (endRow !== undefined && endRow < table.rows.length) {
            /* See if we got lucky and found it in the last row. */
            if (getLineNum(table.rows[endRow]) === lineNum) {
                return table.rows[endRow];
            }
        } else if (row) {
            /*
             * We collapsed the rows (unless someone mucked with the DB),
             * so the desired row is less than the row number retrieved.
             */
            high = Math.min(high, rowOffset + lineNum);
        }

        /* Binary search for this cell. */
        for (i = Math.round((low + high) / 2); low < high - 1;) {
            row = table.rows[rowOffset + i];

            if (!row) {
                /* This should not happen, unless we miscomputed high. */
                high--;

                /*
                 * This won't do much if low + high is odd, but we'll catch
                 * up on the next iteration.
                 */
                i = Math.round((low + high) / 2);
                continue;
            }

            value = getLineNum(row);

            if (!value) {
                /*
                 * Bad luck, let's look around.
                 *
                 * We'd expect to find a value on the first try, but the
                 * following makes sure we explore all rows.
                 */
                found = false;

                for (j = 1; j <= (high - low) / 2; j++) {
                    row = table.rows[rowOffset + i + j];

                    if (row && getLineNum(row)) {
                        i = i + j;
                        found = true;
                        break;
                    } else {
                        row = table.rows[rowOffset + i - j];

                        if (row && getLineNum(row)) {
                            i = i - j;
                            found = true;
                            break;
                        }
                    }
                }

                if (found) {
                    value = getLineNum(row);
                } else {
                    return null;
                }
            }

            /* See if we can use simple math to find the row quickly. */
            guessRowNum = lineNum - value + rowOffset + i;

            if (guessRowNum >= 0 && guessRowNum < table.rows.length) {
                guessRow = table.rows[guessRowNum];

                if (guessRow && getLineNum(guessRow) === lineNum) {
                    /* We found it using maths! */
                    return guessRow;
                }
            }

            oldHigh = high;
            oldLow = low;

            if (value > lineNum) {
                high = i;
            } else if (value < lineNum) {
                low = i;
            } else {
                return row;
            }

            /*
             * Make sure we don't get stuck in an infinite loop. This can happen
             * when a comment is placed in a line that isn't being shown.
             */
            if (oldHigh === high && oldLow === low) {
                break;
            }

            i = Math.round((low + high) / 2);
        }

        // Well.. damn. Ignore this then.
        return null;
    },

    /*
     * Places a CommentBlockView on the page.
     *
     * This will compute the row range for the CommentBlockView and then
     * render it to the screen, if the row range exists.
     *
     * If it doesn't exist yet, the CommentBlockView will be stored in the
     * list of hidden comment blocks for later rendering.
     */
    _placeCommentBlockView: function(commentBlockView) {
        var commentBlock = commentBlockView.model,
            numLines = commentBlock.getNumLines(),
            beginLineNum = commentBlock.get('beginLineNum'),
            endLineNum = commentBlock.get('endLineNum'),
            beginRowEl = this._findLineNumRow(beginLineNum),
            prevBeginRowIndex,
            endRowEl;

        if (beginRowEl) {
            prevBeginRowIndex = beginRowEl.rowIndex;

            endRowEl = (endLineNum === beginLineNum
                        ? beginRowEl
                        : this._findLineNumRow(
                            endLineNum,
                            prevBeginRowIndex,
                            prevBeginRowIndex + numLines - 1));

            /*
             * Note that endRow might be null if it exists in a collapsed
             * region, so we can get away with just using beginRow if we
             * need to.
             */
            commentBlockView.setRows($(beginRowEl), $(endRowEl || beginRowEl));
            commentBlockView.$el.appendTo(
                commentBlockView.$beginRow[0].cells[0]);
            this._visibleCommentBlockViews.push(commentBlockView);
        } else {
            this._hiddenCommentBlockViews.push(commentBlockView);
        }

        return prevBeginRowIndex;
    },

    /*
     * Places any hidden comment blocks onto the diff viewer.
     */
    _placeHiddenCommentBlockViews: function() {
        var hiddenCommentBlockViews = this._hiddenCommentBlockViews,
            prevBeginRowIndex;

        this._hiddenCommentBlockViews = [];

        _.each(hiddenCommentBlockViews, function(commentBlockView) {
            prevBeginRowIndex = this._placeCommentBlockView(commentBlockView,
                                                            prevBeginRowIndex);
        }, this);
    },

    _hideRemovedCommentBlockViews: function() {
        var visibleCommentBlockViews = this._visibleCommentBlockViews;

        this._visibleCommentBlockViews = [];

        _.each(visibleCommentBlockViews, function(commentBlockView) {
            if (commentBlockView.$el.is(':visible')) {
                this._visibleCommentBlockViews.push(commentBlockView);
            } else {
                this._hiddenCommentBlockViews.push(commentBlockView);
            }
        }, this);

        /*
         * Sort these by line number so we can efficiently place them later.
         */
        _.sortBy(this._hiddenCommentBlockViews, function(commentBlockView) {
            return commentBlockView.model.get('beginLineNum');
        });
    },

    /*
     * Update the positions of the collapse buttons.
     *
     * This will attempt to position the collapse buttons such that they're
     * in the center of the exposed part of the expanded chunk in the current
     * viewport.
     *
     * As the user scrolls, they'll be able to see the button scroll along
     * with them. It will not, however, leave the confines of the expanded
     * chunk.
     */
    _updateCollapseButtonPos: function() {
        var windowTop,
            windowHeight,
            len = this._$collapseButtons.length,
            $button,
            $tbody,
            parentOffset,
            parentTop,
            parentHeight,
            btnRight,
            $btnParent,
            parentLeft,
            i,
            y1,
            y2;

        if (len === 0) {
            return;
        }

        windowTop = this._$window.scrollTop();
        windowHeight = this._$window.height();

        for (i = 0; i < len; i++) {
            $button = $(this._$collapseButtons[i]);
            $tbody = $button.parents('tbody');
            parentOffset = $tbody.offset();
            parentTop = parentOffset.top;
            parentHeight = $tbody.height();
            btnRight = $button.data('rb-orig-right');

            if (btnRight === undefined) {
                /*
                 * We need to do this because on Firefox, the computed "right"
                 * position will change when we move the element, causing things
                 * to jump. We're really just trying to look up what the
                 * default is, so do that once and cache.
                 */
                btnRight = parseInt($button.css('right'), 10);
                $button.data('rb-orig-right', btnRight);
            }

            /*
             * We're going to first try to limit our processing to expanded
             * chunks that are currently on the screen. We'll skip over any
             * before those chunks, and stop once we're sure we have no further
             * ones we can show.
             */
            if (parentTop >= windowTop + windowHeight) {
                /* We hit the last one, so we're done. */
                break;
            } else if (parentTop + parentHeight <= windowTop) {
                /* We're not there yet. */
            } else {
                /* Center the button in the view. */
                if (   windowTop >= parentTop
                    && windowTop + windowHeight <= parentTop + parentHeight) {
                    if ($button.css('position') !== 'fixed') {
                        $btnParent = $button.parent();
                        parentLeft = $btnParent.offset().left;

                        /*
                         * Position this fixed in the center of the screen.
                         * It'll be less jumpy.
                         */
                        $button.css({
                            position: 'fixed',
                            left: $button.offset().left,
                            top: Math.round((windowHeight -
                                             $button.outerHeight()) / 2)
                        });
                    }

                    /*
                     * Since the expanded chunk is taking up the whole screen,
                     * we have nothing else to process, so break.
                     */
                    break;
                } else {
                    y1 = Math.max(windowTop, parentTop);
                    y2 = Math.min(windowTop + windowHeight,
                                  parentTop + parentHeight);

                    /*
                     * The area doesn't take up the entire height of the
                     * view. Switch back to an absolute position.
                     */
                    $button.css({
                        position: 'absolute',
                        left: '',
                        top: y1 - parentTop +
                             Math.round((y2 - y1 - $button.outerHeight()) / 2)
                    });
                }
            }
        }
    },

    /*
     * Expands or collapses a chunk in a diff.
     *
     * This is called internally when an expand or collapse button is pressed
     * for a chunk. It will fetch the diff and render it, displaying any
     * contained comments, and setting up the resulting expand or collapse
     * buttons.
     */
    _expandOrCollapse: function($btn, expanding) {
        var chunkIndex = $btn.data('chunk-index'),
            linesOfContext = $btn.data('lines-of-context');

        this.model.getRenderedDiffFragment({
            chunkIndex: chunkIndex,
            linesOfContext: linesOfContext
        }, {
            success: function(html) {
                var $tbody = $btn.parents('tbody'),
                    $scrollAnchor,
                    tbodyID,
                    scrollAnchorID,
                    scrollOffsetTop,
                    newEl;

                /*
                 * We want to position the new chunk or collapse button at
                 * roughly the same position as the chunk or collapse button
                 * that the user pressed. Figure out what it is exactly and what
                 * the scroll offsets are so we can later reposition the scroll
                 * offset.
                 */
                if (expanding) {
                    $scrollAnchor = this.$el;
                    scrollAnchorID = $scrollAnchor[0].id;

                    if (linesOfContext === 0) {
                        /*
                         * We've expanded the entire chunk, so we'll be looking
                         * for the collapse button.
                         */
                        tbodyID = /collapsed-(.*)/.exec(scrollAnchorID)[1];
                    } else {
                        tbodyID = scrollAnchorID;
                    }
                } else {
                    $scrollAnchor = $btn;
                }

                scrollOffsetTop = $scrollAnchor.offset().top -
                                  this._$window.scrollTop();

                /*
                 * If we already expanded, we may have one or two loaded chunks
                 * adjacent to the header. We want to remove those, since we'll
                 * be generating new ones that include that data.
                 */
                $tbody.prev('.diff-header, .loaded').remove();
                $tbody.next('.diff-header, .loaded').remove();

                /*
                 * Replace the header with the new HTML. This may also include a
                 * new header.
                 */
                $tbody.replaceWith(html);

                if (expanding) {
                    this._placeHiddenCommentBlockViews();
                } else {
                    this._hideRemovedCommentBlockViews();
                }

                /*
                 * Get the new tbody for the header, if any, and try to center.
                 */
                if (tbodyID) {
                    newEl = document.getElementById(tbodyID);

                    if (newEl) {
                        $scrollAnchor = $(newEl);

                        if ($scrollAnchor.length > 0) {
                            this._$window.scrollTop(
                                $scrollAnchor.offset().top -
                                scrollOffsetTop);
                        }
                    }
                }

                /* Recompute the list of buttons for later use. */
                this._$collapseButtons = this.$('.diff-collapse-btn');
                this._updateCollapseButtonPos();

                this.trigger('chunkExpansionChanged');
            }
        }, this);
    },

    /*
     * Handler for when the file header is clicked.
     *
     * Highlights the file header.
     */
    _onFileHeaderClicked: function() {
        this.trigger('fileClicked');

        return false;
    },

    /*
     * Handler for clicks on a "Moved to/from" flag.
     *
     * This will scroll to the location on the other end of the move,
     * and briefly highlight the line.
     */
    _onMovedLineClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this.trigger('moveFlagClicked', $(e.target).data('line'));
    },

    /*
     * Handles the mouse up event.
     *
     * This will select any chunk that was clicked, highlight the chunk,
     * and ensure it's cleanly scrolled into view.
     */
    _onMouseUp: function(e) {
        var node = e.target,
            $tbody;

        /*
         * The user clicked somewhere else. Move the anchor point here
         * if it's part of the diff.
         */
        $tbody = $(node).parents('tbody:first');

        if ($tbody.length > 0 &&
            ($tbody.hasClass('delete') ||
             $tbody.hasClass('insert') ||
             $tbody.hasClass('replace'))) {
            this.trigger('chunkClicked', $tbody.find('a:first').attr('name'));
        }
    },

    /*
     * Handler for Expand buttons.
     *
     * The Expand buttons will expand a collapsed chunk, either entirely
     * or by certain amounts. It will fetch the new chunk contents and
     * inject it into the diff viewer.
     */
    _onExpandChunkClicked: function(e) {
        var $target = $(e.target);

        if (!$target.hasClass('diff-expand-btn')) {
            /* We clicked an image inside the link. Find the parent. */
            $target = $target.parents('.diff-expand-btn');
        }

        e.preventDefault();
        this._expandOrCollapse($target, true);
    },

    /*
     * Handler for the Collapse button.
     *
     * The fully collapsed representation of that chunk will be fetched
     * and put into the diff viewer in place of the expanded chunk.
     */
    _onCollapseChunkClicked: function(e) {
        var $target = $(e.target);

        if (!$target.hasClass('diff-collapse-btn')) {
            /* We clicked an image inside the link. Find the parent. */
            $target = $target.parents('.diff-collapse-btn');
        }

        e.preventDefault();
        this._expandOrCollapse($target, false);
    }
});


})();
