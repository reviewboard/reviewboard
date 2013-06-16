RB.DiffReviewableView = RB.AbstractReviewableView.extend({
    tagName: 'table',

    commentBlockView: RB.AbstractCommentBlockView,
    commentsListName: 'diff_comments',

    initialize: function() {
        RB.AbstractReviewableView.prototype.initialize.call(this);
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
            k;

        if (table.rows.length - rowOffset > lineNum) {
            row = table.rows[rowOffset + lineNum];

            // Account for the "x lines hidden" row.
            if (row !== null && this._getLineNum(row) === lineNum) {
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
            if (this._getLineNum(table.rows[endRow]) === lineNum) {
                return table.rows[endRow];
            }
        } else if (row !== null) {
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

            value = this._getLineNum(row);

            if (!value) {
                /*
                 * Bad luck, let's look around.
                 *
                 * We'd expect to find a value on the first try, but the
                 * following makes sure we explore all rows.
                 */
                found = false;

                for (k = 1; k <= (high - low) / 2; k++) {
                    row = table.rows[rowOffset + i + k];

                    if (row && this._getLineNum(row)) {
                        i = i + k;
                        found = true;
                        break;
                    } else {
                        row = table.rows[rowOffset + i - k];

                        if (row && this._getLineNum(row)) {
                            i = i - k;
                            found = true;
                            break;
                        }
                    }
                }

                if (found) {
                    value = this._getLineNum(row);
                } else {
                    return null;
                }
            }

            /* See if we can use simple math to find the row quickly. */
            guessRowNum = lineNum - value + rowOffset + i;

            if (guessRowNum >= 0 && guessRowNum < table.rows.length) {
                guessRow = table.rows[guessRowNum];

                if (guessRow && this._getLineNum(guessRow) === lineNum) {
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
     * Returns the line number for a row.
     */
    _getLineNum: function(row) {
        return parseInt(row.getAttribute('line'), 10);
    }
});
