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
        var $commentFlag,
            commentBlock;

        $row.removeClass('selected');

        if (this._beginLineNum === this._endLineNum) {
            /* See if we have a comment flag on the selected row. */
            $commentFlag = $row.find('.commentflag');

            if ($commentFlag.length === 1) {
                $commentFlag.click()
                return;
            }
        }

        /*
         * Selection was finalized. Create the comment block
         * and show the comment dialog.
         */
        commentBlock = new RB.DiffCommentBlock(this._$begin,
                                               this._$end,
                                               this._beginLineNum,
                                               this._endLineNum);
        commentBlock.showCommentDlg();
    },

    /*
     * Adds a row to the selection. This will update the selection range
     * and mark the rows as selected.
     *
     * This row is assumed to be the most recently selected row, and
     * will mark the new beginning or end of the selection.
     */
    _addRow: function($row) {
        var $lineNumCell,
            lineNum,
            min,
            max,
            i;

        if (this._$begin) {
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
        } else {
            $lineNumCell = $($row[0].cells[0]);

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
        }
    },

    /*
     * Removes any old rows from the selection, based on the most recent
     * row selected.
     */
    _removeOldRows: function($row) {
        var destRowIndex = $row[0].rowIndex,
            i;

        if (destRowIndex >= this._$begin[0].rowIndex) {
            for (i = this._lastSeenIndex;
                 i > destRowIndex;
                 i--) {
                $(this.el.rows[i]).removeClass('selected');
            }

            this._lastSeenIndex = destRowIndex;
        }
    },

    /*
     * Resets the selection information.
     */
    _reset: function() {
        var rows,
            i;

        if (this._$begin) {
            /* Reset the selection. */
            rows = this.el.rows;

            for (i = this._$begin[0].rowIndex;
                 i <= this._$end[0].rowIndex;
                 i++) {
                $(rows[i]).removeClass('selected');
            }

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
        var node = e.target,
            $tbody;

        if (this._$ghostCommentFlagCell) {
            node = this._$ghostCommentFlagCell[0];
        }

        if (this._isLineNumCell(node)) {
            this._end(this._getActualLineNumCell($(node)).parent());
            e.stopImmediatePropagation();
        }

        this._reset();

        return false;
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
            this._addRow($row);
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

    commentBlockView: RB.AbstractCommentBlockView,
    commentsListName: 'diff_comments',

    events: {
        'mouseup': '_onMouseUp'
    },

    /*
     * Initializes the reviewable for a file's diff.
     */
    initialize: function() {
        RB.AbstractReviewableView.prototype.initialize.call(this);

        this._selector = new CommentRowSelector({
            el: this.el
        });
    },

    /*
     * Removes the reviewable from the DOM.
     */
    remove: function() {
        RB.AbstractReviewableView.prototype.remove.call(this);

        this._selector.remove();
    },

    /*
     * Renders the reviewable.
     */
    render: function() {
        this._selector.render();

        return this;
    },

    /*
     * Finds the row in a table matching the specified line number.
     *
     * This will perform a binary search of the lines trying to find
     * the matching line number. It will then return the row element,
     * if found.
     */
    findLineNumRow: function(lineNum, startRow, endRow) {
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
     * Sets the active anchor on the page, optionally scrolling to it.
     */
    _gotoAnchor: function(name, scroll) {
        return RB.scrollToAnchor($("a[name='" + name + "']"), scroll || false);
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
            this._gotoAnchor($tbody.find('a:first').attr('name'), true);
        }
    }
});


})();
