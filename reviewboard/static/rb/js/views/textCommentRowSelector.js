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

    linkTemplate: _.template([
    '<th>',
        '<a href="<%- linkToRow %>" class="copylink"><%- lineNumber %></a>',
    '</th>'
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

        this._oldLinkLineNum = 0;
        this._oldLinkRow = null;
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

        this._$link = $(this.linkTemplate({
            lineNumber: this.lineNumber,
            linkToRow: this.linkToRow
        }));
        this._$link.on({
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
     * Adds a link to code line number, when the code line number is hovered.
     */
    _addLinkToCopy: function($row) {
        var lineNum,
            file,
            trLine,
            linkToCodeLine,
            commentFlag;

        /* This ensures, that the link is added only when the row changes. */
        if (this._oldLinkRow === null ||
            this._oldLinkLineNum !== $row.attr('line')) {
            if (this._oldLinkRow !== null) {
                /* Remove the previous link, when user is on different row. */
                this._removeLinkToCopy(this._oldLinkRow);
            }
            /*
             * File id and line number should be
             * enough to identify the right row.
             */
            lineNum = this.getLineNum($row[0]);
            file = $row.parents('table')[0].id;
            trLine = $row.attr('line');
            linkToCodeLine = '#' + file + ',' + trLine;

            /*
             * Note:
             * first() and last() selectors are used below to get or insert
             * the exact line numbers in case of two column diff.
             *
             * First we try clone the comment flag, it doesn't matter if it
             * doesn't exist. The first column code line number is saved
             * to lineNum variable. We use the template to replace the th with
             * a link. After the link is inserted, we append the possible
             * comment flag to the element.
             */
            commentFlag = $row.find('.commentflag').clone();
            $row.find('.commentflag').remove();
            lineNum = $row.find('th').first().text();
            $row.find('th')
                .first()
                .replaceWith(this.linkTemplate({
                    lineNumber: lineNum,
                    linkToRow: linkToCodeLine
                }));
            commentFlag.appendTo($row.find('th').first());

            /*
             * If the diff has two columns, we have to replace the second line
             * number also with a link. The last() selector is used
             * to get the second columns code line number.
             */
            if ($row.find('th').length > 1) {
                lineNum = $row.children('th').last().text();
                $row.children('th').last()
                    .replaceWith(this.linkTemplate({
                        lineNumber: lineNum,
                        linkToRow: linkToCodeLine
                    }));
            }
            this._highlightRow($row);
            this._oldLinkLineNum = $row.attr('line');
            this._oldLinkRow = $row;
        }
    },

    /*
     * Removes the the code line link when hover has moved on.
     */
    _removeLinkToCopy: function($row) {
        var lineNum,
            commentFlag;

        lineNum = this.getLineNum($row[0]);
        if (lineNum) {
            /*
             * Note:
             * first() and last() selectors are used below to get or insert
             * the exact line numbers in case of two column diff.
             *
             * First we clone the possible comment flag, it doesn't matter if
             * the flag doesn't exist. Then we remove the comment flag to get
             * easier access to the line number. The link is removed by adding
             * the line number as a text to th element.
             * After the line number is in place, we append the possible
             * comment flag to the element.
             */

            commentFlag = $row.find('.commentflag').clone();
            $row.find('.commentflag').remove();
            lineNum = $row.find('th').first().text();
            $row.find('th').first().text(lineNum);
            commentFlag.appendTo($row.find('th').first());

            /*
             * If the diff has two columns, we have return the basic line
             * number also to the second column. The last() selector is used
             * to get the second columns code line number.
             */
            if ($row.find('th').length > 1) {
                lineNum = $row.find('th').last().text();
                $row.find('th').last().text(lineNum);
            }
            $row.removeClass('selected');
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
            // Navigate up out of <a class="copylink"> elements
            if ($node.hasClass('copylink')) {
                $node = $node.parent();
            }
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

        if (e.button === 0) {
            if (this._$ghostCommentFlagCell) {
                node = this._$ghostCommentFlagCell[0];
            }

            if (this._isLineNumCell(node)) {
                this._begin($(node.parentNode));
                return false;
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
            this._addLinkToCopy($row);
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
