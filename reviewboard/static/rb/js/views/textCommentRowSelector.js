(function() {


/*
 * Provides multi-line commenting capabilities for a diff.
 *
 * This tacks on commenting capabilities onto a DiffReviewableView's
 * element. It listens for mouse events that begin/end the creation of
 * a new comment.
 */
RB.TextCommentRowSelector = Backbone.View.extend({
    ghostCommentFlagTemplate: _.template([
        '<span class="commentflag ghost-commentflag">',
        ' <span class="commentflag-shadow"></span>',
        ' <span class="commentflag-inner"></span>',
        '</span>'
    ].join('')),

    events: {
        'copy': '_onCopy',
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
        this._selectionClass = null;

        /*
         * Support setting the clipboard only if we have the necessary
         * functions. This may still be turned off later if we can't
         * actually set the data.
         */
        this._supportsSetClipboard = (
            window.getSelection !== undefined &&
            window.Range !== undefined &&
            window.Range.prototype.cloneContents !== undefined);

        this._newlineChar = null;

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
    * Creates a comment for a chunk of a diff.
    */
    createComment: function(beginLineNum, endLineNum, beginNode, endNode) {
        this._beginLineNum = beginLineNum;
        this._endLineNum = endLineNum;
        this._$begin = this._getActualLineNumCell($(beginNode)).parent();
        this._$end = this._getActualLineNumCell($(endNode)).parent();

        if (this._isLineNumCell(endNode)) {
            this._end(this._getActualLineNumCell($(endNode)).parent());
        }

        this._reset();
    },

    /*
     * Return the beginning and end rows for a given line number range.
     *
     * If the first line number corresponds to a valid row within the table,
     * an array will be returned containing the DOM elements for the
     * two rows matching the two line numbers. If the second line number
     * could not be found, its entry in the array will be null.
     *
     * If the first line number could not be found, null is returned instead
     * of an array.
     *
     * A minimum rowIndex can be provided in order to constrain the search.
     * No rows prior to that minimum rowIndex will be searched.
     */
    getRowsForRange: function(beginLineNum, endLineNum, minRowIndex) {
        var beginRowEl = this.findLineNumRow(beginLineNum, minRowIndex),
            endRowEl,
            rowIndex;

        if (beginRowEl) {
            rowIndex = beginRowEl.rowIndex;

            endRowEl = (endLineNum === beginLineNum
                        ? beginRowEl
                        : this.findLineNumRow(
                            endLineNum,
                            rowIndex,
                            rowIndex + endLineNum - beginLineNum));

            return [beginRowEl, endRowEl];
        } else {
            return null;
        }
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
            if (row && this.getLineNum(row) === lineNum) {
                return row;
            }
        }

        if (startRow) {
            // startRow already includes the offset, so we need to remove it.
            startRow -= rowOffset;
        }

        low = startRow || 0;
        high = Math.min(endRow || table.rows.length, table.rows.length);

        if (endRow !== undefined && endRow < table.rows.length) {
            // See if we got lucky and found it in the last row.
            if (this.getLineNum(table.rows[endRow]) === lineNum) {
                return table.rows[endRow];
            }
        } else if (row) {
            /*
             * We collapsed the rows (unless someone mucked with the DB),
             * so the desired row is less than the row number retrieved.
             */
            high = Math.min(high, rowOffset + lineNum);
        }

        // Binary search for this cell.
        for (i = Math.round((low + high) / 2); low < high - 1;) {
            row = table.rows[rowOffset + i];

            if (!row) {
                // This should not happen, unless we miscomputed high.
                high--;

                /*
                 * This won't do much if low + high is odd, but we'll catch
                 * up on the next iteration.
                 */
                i = Math.round((low + high) / 2);
                continue;
            }

            value = this.getLineNum(row);

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

                    if (row && this.getLineNum(row)) {
                        i = i + j;
                        found = true;
                        break;
                    } else {
                        row = table.rows[rowOffset + i - j];

                        if (row && this.getLineNum(row)) {
                            i = i - j;
                            found = true;
                            break;
                        }
                    }
                }

                if (found) {
                    value = this.getLineNum(row);
                } else {
                    return null;
                }
            }

            // See if we can use simple math to find the row quickly.
            guessRowNum = lineNum - value + rowOffset + i;

            if (guessRowNum >= 0 && guessRowNum < table.rows.length) {
                guessRow = table.rows[guessRowNum];

                if (guessRow && this.getLineNum(guessRow) === lineNum) {
                    // We found it using maths!
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
     * Begins the selection of line numbers.
     */
    _begin: function($row) {
        var lineNum = this.getLineNum($row[0]);

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
        lineNum = this.getLineNum($row[0]);

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
                this._beginLineNum = this.getLineNum($row[0]);
            } else {
                /*
                 * We're removing from the bottom of the selection. The end
                 * location will need to be moved.
                 */
                this._removeSelectionClasses(destRowIndex,
                                             this._lastSeenIndex);

                this._$end = $row;
                this._endLineNum = this.getLineNum($row[0]);
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
     * Handler for when the user copies text in a column.
     *
     * This will begin the process of capturing any selected text in
     * a column to the clipboard in a cross-browser way.
     */
    _onCopy: function(e) {
        var clipboardData = e.originalEvent.clipboardData ||
                            window.clipboardData;

        if (clipboardData && this._supportsSetClipboard &&
            this._copySelectionToClipboard(clipboardData)) {
            /*
             * Prevent the default copy action from occurring.
             */
            return false;
        }
    },

    /*
     * Copies the current selection to the clipboard.
     *
     * This will locate the desired text to copy, based on the selection
     * range within the column where selection started. It will then
     * extract the code from the <pre> tags and build a string to set in
     * the clipboard.
     *
     * This requires support in the browser for setting clipboard contents
     * on copy. If the browser does not support this, the default behavior
     * will be used.
     */
    _copySelectionToClipboard: function(clipboardData) {
        var sel = window.getSelection(),
            s = '',
            tdClass,
            range,
            doc,
            nodes,
            i,
            j;

        if (this._newlineChar === null) {
            /*
             * Figure out what newline character should be used on this
             * platform. Ideally, we'd determine this from some browser
             * behavior, but it doesn't seem that can be consistently
             * determined.
             */
            if (navigator.appVersion.indexOf('Win') !== -1) {
                this._newlineChar = '\r\n';
            } else {
                this._newlineChar = '\n';
            }
        }

        if (this._selectedCellIndex === 3 || this.$el.hasClass('newfile')) {
            tdClass = 'r';
        } else {
            tdClass = 'l';
        }

        for (i = 0; i < sel.rangeCount; i++) {
            range = sel.getRangeAt(i);

            if (range.collapsed) {
                continue;
            }

            doc = range.cloneContents();
            nodes = doc.querySelectorAll('td.' + tdClass + ' pre');

            /*
             * The selection spans multiple rows. Find the blocks of text
             * in the column we want, and copy those to the clipboard.
             */
            if (nodes.length > 0) {
                for (j = 0; j < nodes.length; j++) {
                    s += nodes[j].textContent;

                    /*
                     * We only want to include a newline if this isn't the
                     * last node, or the boundary ends within an element
                     * (likely <pre>, but possibly another) and isn't ending
                     * at the beginning of that element.
                     *
                     * This prevents a newline from appearing at the end of
                     * a selection if the selection ends in the middle of a
                     * line of code.
                     */
                    if (j < nodes.length - 1 ||
                        (range.endContainer.nodeType === Node.ELEMENT_NODE &&
                         range.endOffset > 0)) {
                        s += this._newlineChar;
                    }
                }
            } else if (sel.rangeCount === 1) {
                /*
                 * If we're here, then we selected a subset of a single
                 * cell. There was only one Range, and no <pre> tags as
                 * part of it. We can just grab the text of the document.
                 *
                 * (We don't really need to break here, but we're going to
                 * in order to be clear that we're completely done.)
                 */
                s = $(doc).text();
                break;
            }
        }

        try {
            clipboardData.setData('text', s);
        } catch (e) {
            /* Let the native behavior take over. */
            this._supportsSetClipboard = false;
            return false;
        }

        return true;
    },

    /*
     * Handles the mouse down event, which begins selection for comments.
     */
    _onMouseDown: function(e) {
        var node = e.target,
            $node;

        if (this._selectionClass) {
            this.$el.removeClass(this._selectionClass);
        }

        if (this._$ghostCommentFlagCell) {
            node = this._$ghostCommentFlagCell[0];
        }

        if (this._isLineNumCell(node)) {
            this._begin($(node.parentNode));
            return false;
        } else {
            if (node.tagName === 'TD') {
                $node = $(node);
            } else {
                $node = $(node).parentsUntil('tr', 'td');
            }

            if ($node.length > 0) {
                this._selectionClass = 'selecting-col-' + $node[0].cellIndex;
                this._selectedCellIndex = $node[0].cellIndex;
                this.$el.addClass(this._selectionClass);
            }
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
    },

    /*
     * Returns the line number for a row.
     */
    getLineNum: function(row) {
        return parseInt(row.getAttribute('line'), 10);
    }
});


})();
