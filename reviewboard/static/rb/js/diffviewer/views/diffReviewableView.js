(function() {


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

    cssTemplate: _.template([
        '#<%= id %> td pre,',
        '#<%= id %> .revision-row th.revision-col {',
        '    min-width: <%= minColWidth %>px;',
        '    max-width: <%= maxColWidth %>px;',
        '}',
        '#<%= id %> .filename-row th {',
        '    min-width: <%= minFilenameWidth %>px;',
        '    max-width: <%= maxFilenameWidth %>px;',
        '}'
    ].join('\n')),

    events: {
        'click .download-link': '_onDownloadLinkClicked',
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
        _super(this).initialize.call(this);

        _.bindAll(this, '_updateCollapseButtonPos', '_onWindowResize');

        this._selector = new RB.TextCommentRowSelector({
            el: this.el,
            reviewableView: this
        });

        this._hiddenCommentBlockViews = [];
        this._visibleCommentBlockViews = [];
        this._$collapseButtons = $();

        /* State for keeping consistent column widths for diff content. */
        this._$filenameRow = null;
        this._$revisionRow = null;
        this._$css = null;
        this._filenameReservedWidths = 0;
        this._colReservedWidths = 0;
        this._numColumns = 0;
        this._numFilenameColumns = 0;
        this._prevContentWidth = null;

        /*
         * Wrap this only once so we don't have to re-wrap every time
         * the page scrolls.
         */
        this._$window = $(window);
        this._$parent = this.$el.parent();

        this.on('commentBlockViewAdded', this._placeCommentBlockView, this);
    },

    /*
     * Removes the reviewable from the DOM.
     */
    remove: function() {
        RB.AbstractReviewableView.prototype.remove.call(this);

        this._$window.off('scroll', this._updateCollapseButtonPos);
        this._$window.off('resize', this._onWindowResize);

        this._selector.remove();
    },

    /*
     * Renders the reviewable.
     */
    render: function() {
        var $thead;

        _super(this).render.call(this);

        $thead = this.$('thead');

        this._$revisionRow = $thead.find('.revision-row');
        this._$filenameRow = $thead.find('.filename-row');
        this._$css = $('<style/>').appendTo(this.$el);

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

        this._precalculateContentWidths();
        this._updateColumnSizes();

        this._$window.on('scroll', this._updateCollapseButtonPos);
        this._$window.on('resize', this._onWindowResize);

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
    * Creates a comment for a chunk of a diff.
    */
    createComment: function(beginLineNum, endLineNum, beginNode, endNode) {
        this._selector.createComment(beginLineNum, endLineNum, beginNode,
                                     endNode);
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
            if (row && this.getLineNum(row) === lineNum) {
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

            /* See if we can use simple math to find the row quickly. */
            guessRowNum = lineNum - value + rowOffset + i;

            if (guessRowNum >= 0 && guessRowNum < table.rows.length) {
                guessRow = table.rows[guessRowNum];

                if (guessRow && this.getLineNum(guessRow) === lineNum) {
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

                /*
                 * We'll need to update the column sizes, but first, we need
                 * to re-calculate things like the line widths, since they
                 * may be longer after expanding.
                 */
                this._precalculateContentWidths();
                this._updateColumnSizes();

                this.trigger('chunkExpansionChanged');
            }
        }, this);
    },

    /*
     * Pre-calculate the widths and other state needed for column widths.
     *
     * This will store the number of columns and the reserved space that
     * needs to be subtracted from the container width, to be used in later
     * calculating the desired widths of the content areas.
     */
    _precalculateContentWidths: function() {
        var $cells,
            containerExtents,
            cellPadding;

        if (!this.$el.hasClass('diff-error') && this._$revisionRow.length > 0) {
            containerExtents = this.$el.getExtents('p', 'lr');

            /* Calculate the widths and state of the diff columns. */
            $cells = $(this._$revisionRow[0].cells);
            cellPadding = this.$('pre:first').parent().andSelf()
                .getExtents('p', 'lr');

            this._colReservedWidths = $cells.eq(0).outerWidth() + cellPadding +
                                      containerExtents;
            this._numColumns = $cells.length;

            if (this._numColumns === 4) {
                /* There's a left-hand side and a right-hand side. */
                this._colReservedWidths += $cells.eq(2).outerWidth() +
                                           cellPadding;
            }

            /* Calculate the widths and state of the filename columns. */
            $cells = $(this._$filenameRow[0].cells);
            cellPadding = $cells.eq(0).getExtents('p', 'lr');
            this._numFilenameColumns = $cells.length;
            this._filenameReservedWidths = containerExtents +
                                           2 * this._numFilenameColumns;
        } else {
            this._colReservedWidths = 0;
            this._filenameReservedWidths = 0;
            this._numColumns = 0;
            this._numFilenameColumns = 0;
        }
    },

    /*
     * Update the sizes of the diff content columns.
     *
     * This will figure out the minimum and maximum widths of the columns
     * and set them in a stylesheet, ensuring that lines will constrain to
     * those sizes (force-wrapping if necessary) without overflowing or
     * causing the other column to shrink too small.
     */
    _updateColumnSizes: function() {
        var fullWidth,
            contentWidth,
            filenameWidth;

        if (this.$el.hasClass('diff-error')) {
            return;
        }

        fullWidth = this._$parent.width();

        /* Calculate the desired widths of the diff columns. */
        contentWidth = fullWidth - this._colReservedWidths;

        if (this._numColumns === 4) {
            contentWidth /= 2;
        }

        /* Calculate the desired widths of the filename columns. */
        filenameWidth = fullWidth - this._filenameReservedWidths;

        if (this._numFilenameColumns === 2) {
            filenameWidth /= 2;
        }

        if (contentWidth !== this._prevContentWidth ||
            filenameWidth !== this._prevFilenameWidth) {
            /* The widths have changed, so force new minimums and maximums. */
            this._$css.html(this.cssTemplate({
                id: this.el.id,
                minColWidth: Math.ceil(contentWidth * 0.66),
                maxColWidth: Math.ceil(contentWidth),
                minFilenameWidth: Math.ceil(filenameWidth * 0.66),
                maxFilenameWidth: Math.ceil(filenameWidth)
            }));

            this._prevContentWidth = contentWidth;
            this._prevFilenameWidth = filenameWidth;
        }
    },

    /*
     * Handler for when the window resizes.
     *
     * Updates the sizes of the diff columns, and the location of the
     * collapse buttons (if one or more are visible).
     */
    _onWindowResize: function() {
        this._updateColumnSizes();
        this._updateCollapseButtonPos();
    },

    /*
     * Handler for when a file download link is clicked.
     *
     * Prevents the event from bubbling up and being caught by
     * _onFileHeaderClicked.
     */
    _onDownloadLinkClicked: function(e) {
        e.stopPropagation();
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
    },

    /*
     * Returns the line number for a row.
     */
    getLineNum: function(row) {
        return parseInt(row.getAttribute('line'), 10);
    }
});


})();
