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
        'click .download-link': '_onDownloadLinkClicked',
        'click thead tr': '_onFileHeaderClicked',
        'click .moved-to, .moved-from': '_onMovedLineClicked',
        'click .diff-collapse-btn': '_onCollapseChunkClicked',
        'click .diff-expand-btn': '_onExpandChunkClicked',
        'click .show-deleted-content-action': '_onShowDeletedClicked',
        'mouseup': '_onMouseUp'
    },

    /**
     * Initialize the reviewable for a file's diff.
     */
    initialize() {
        RB.AbstractReviewableView.prototype.initialize.call(this);

        this._selector = new RB.TextCommentRowSelector({
            el: this.el,
            reviewableView: this,
        });

        this._hiddenCommentBlockViews = [];
        this._visibleCommentBlockViews = [];

        /* State for keeping consistent column widths for diff content. */
        this._$filenameRow = null;
        this._$revisionRow = null;
        this._filenameReservedWidths = 0;
        this._colReservedWidths = 0;
        this._numColumns = 0;
        this._numFilenameColumns = 0;
        this._prevContentWidth = null;
        this._prevFilenameWidth = null;
        this._prevFullWidth = null;

        /*
         * Wrap this only once so we don't have to re-wrap every time
         * the page scrolls.
         */
        this._$window = $(window);
        this._$parent = this.$el.parent();

        this.on('commentBlockViewAdded', this._placeCommentBlockView, this);
    },

    /**
     * Remove the reviewable from the DOM.
     */
    remove() {
        RB.AbstractReviewableView.prototype.remove.call(this);

        this._selector.remove();
    },

    /**
     * Render the reviewable.
     *
     * Returns:
     *     RB.DiffReviewableView:
     *     This object, for chaining.
     */
    render() {
        RB.AbstractReviewableView.prototype.render.call(this);

        this._centered = new RB.CenteredElementManager();

        const $thead = $(this.el.tHead);

        this._$revisionRow = $thead.children('.revision-row');
        this._$filenameRow = $thead.children('.filename-row');

        this._selector.render();

        _.each(this.$el.children('tbody.binary'), thumbnailEl => {
            const $thumbnail = $(thumbnailEl);
            const id = $thumbnail.data('file-id');
            const $caption = $thumbnail.find('.file-caption .edit');
            const reviewRequest = this.model.get('reviewRequest');
            const fileAttachment = reviewRequest.createFileAttachment({
                id: id,
            });

            if (!$caption.hasClass('empty-caption')) {
                fileAttachment.set('caption', $caption.text());
            }
        });

        this._precalculateContentWidths();
        this._updateColumnSizes();

        return this;
    },

    /*
     * Toggles the display of whitespace-only chunks.
     */
    toggleWhitespaceOnlyChunks() {
        this.$('tbody tr.whitespace-line').toggleClass('dimmed');

        _.each(this.$el.children('tbody.whitespace-chunk'), chunk => {
            const $chunk = $(chunk);
            const dimming = $chunk.hasClass('replace');

            $chunk.toggleClass('replace');

            const $children = $chunk.children();
            $children.first().toggleClass('first');
            $children.last().toggleClass('last');

            const chunkID = chunk.id.split('chunk')[1];

            if (dimming) {
                this.trigger('chunkDimmed', chunkID);
            } else {
                this.trigger('chunkUndimmed', chunkID);
            }
        });

        /*
         * Swaps the visibility of the "This file has whitespace changes"
         * tbody and the chunk siblings.
         */
        this.$el.children('tbody.whitespace-file')
            .siblings('tbody')
            .addBack()
                .toggle();
    },

   /**
    * Create a comment for a chunk of a diff.
    *
    * Args:
    *     beginLineNum (number)
    *         The first line of the diff to comment on.
    *
    *     endLineNum (number):
    *         The last line of the diff to comment on.
    *
    *     beginNode (Element):
    *         The row corresponding to the first line of the diff being
    *         commented upon.
    *
    *     endNode (Element):
    *         The row corresponding to the last line of the diff being
    *         commented upon.
    */
    createComment(beginLineNum, endLineNum, beginNode, endNode) {
        this._selector.createComment(beginLineNum, endLineNum, beginNode,
                                     endNode);
    },

    /**
     * Place a CommentBlockView on the page.
     *
     * This will compute the row range for the CommentBlockView and then
     * render it to the screen, if the row range exists.
     *
     * If it doesn't exist yet, the CommentBlockView will be stored in the
     * list of hidden comment blocks for later rendering.
     *
     * Args:
     *     commentBlockView (RB.DiffCommentBlockView):
     *         The comment block view to place.
     *
     *     prevBeginRowIndex (number):
     *         The row index to begin at. This places a limit on the rows
     *         searched.
     */
    _placeCommentBlockView(commentBlockView, prevBeginRowIndex) {
        const commentBlock = commentBlockView.model;

        const rowEls = this._selector.getRowsForRange(
            commentBlock.get('beginLineNum'),
            commentBlock.get('endLineNum'),
            prevBeginRowIndex);

        if (rowEls !== null) {
            const beginRowEl = rowEls[0];
            const endRowEl = rowEls[1];

            /*
             * Note that endRow might be null if it exists in a collapsed
             * region, so we can get away with just using beginRow if we
             * need to.
             */
            commentBlockView.setRows($(beginRowEl), $(endRowEl || beginRowEl));
            commentBlockView.$el.appendTo(
                commentBlockView.$beginRow[0].cells[0]);
            this._visibleCommentBlockViews.push(commentBlockView);

            return beginRowEl.rowIndex;
        } else {
            this._hiddenCommentBlockViews.push(commentBlockView);
            return prevBeginRowIndex;
        }
    },

    /**
     * Place any hidden comment blocks onto the diff viewer.
     */
    _placeHiddenCommentBlockViews() {
        const hiddenCommentBlockViews = this._hiddenCommentBlockViews;
        this._hiddenCommentBlockViews = [];
        let prevBeginRowIndex;

        for (let i = 0; i < hiddenCommentBlockViews.length; i++) {
            prevBeginRowIndex = this._placeCommentBlockView(
                hiddenCommentBlockViews[i], prevBeginRowIndex);
        }
    },

    /**
     * Mark any comment block views not visible as hidden.
     */
    _hideRemovedCommentBlockViews() {
        const visibleCommentBlockViews = this._visibleCommentBlockViews;
        this._visibleCommentBlockViews = [];

        for (let i = 0; i < visibleCommentBlockViews.length; i++) {
            const commentBlockView = visibleCommentBlockViews[i];

            if (commentBlockView.$el.is(':visible')) {
                this._visibleCommentBlockViews.push(commentBlockView);
            } else {
                this._hiddenCommentBlockViews.push(commentBlockView);
            }
        }

        /* Sort these by line number so we can efficiently place them later. */
        _.sortBy(
            this._hiddenCommentBlockViews,
            commentBlockView => commentBlockView.model.get('beginLineNum'));
    },

    /**
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
    _updateCollapseButtonPos() {
        this._centered.updatePosition();
    },

    /**
     * Expands or collapses a chunk in a diff.
     *
     * This is called internally when an expand or collapse button is pressed
     * for a chunk. It will fetch the diff and render it, displaying any
     * contained comments, and setting up the resulting expand or collapse
     * buttons.
     *
     * Args:
     *     $btn (jQuery):
     *         The expand/collapse button that was clicked.
     *
     *     expanding (boolean):
     *          Whether or not we are expanding.
     */
    _expandOrCollapse($btn, expanding) {
        const chunkIndex = $btn.data('chunk-index');
        const linesOfContext = $btn.data('lines-of-context');

        this.model.getRenderedDiffFragment({
            chunkIndex: chunkIndex,
            linesOfContext: linesOfContext,
        }, {
            success: html => {
                const $tbody = $btn.closest('tbody');
                let tbodyID;
                let $scrollAnchor;
                let scrollAnchorID;

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

                const scrollOffsetTop = ($scrollAnchor.offset().top -
                                         this._$window.scrollTop());

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
                if (tbodyID !== undefined) {
                    const newEl = document.getElementById(tbodyID);

                    if (newEl !== null) {
                        $scrollAnchor = $(newEl);

                        this._$window.scrollTop(
                            $scrollAnchor.offset().top - scrollOffsetTop);
                    }
                }

                /* Recompute the set of buttons for later use. */
                this._centered.setElements(new Map(
                    Array.prototype.map.call(
                        this.$('.diff-collapse-btn'),
                        el => [el, {
                            $top: $(el).closest('tbody'),
                        }])
                ));
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
        });
    },

    /**
     * Pre-calculate the widths and other state needed for column widths.
     *
     * This will store the number of columns and the reserved space that
     * needs to be subtracted from the container width, to be used in later
     * calculating the desired widths of the content areas.
     */
    _precalculateContentWidths() {
        let cellPadding = 0;

        if (!this.$el.hasClass('diff-error') && this._$revisionRow.length > 0) {
            const containerExtents = this.$el.getExtents('p', 'lr');

            /* Calculate the widths and state of the diff columns. */
            let $cells = $(this._$revisionRow[0].cells);
            cellPadding = $(this.el.querySelector('pre'))
                .parent().addBack()
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
    _updateColumnSizes() {
        if (this.$el.hasClass('diff-error')) {
            return;
        }

        let $parent = this._$parent;

        if (!$parent.is(':visible')) {
            /*
             * We're still in diff loading mode, and the parent is hidden. We
             * can get the width we need from the parent. It should be the same,
             * or at least close enough for the first stab at column sizes.
             */
            $parent = $parent.parent();
        }

        const fullWidth = $parent.width();

        if (fullWidth === this._prevFullWidth) {
            return;
        }

        this._prevFullWidth = fullWidth;

        /* Calculate the desired widths of the diff columns. */
        let contentWidth = fullWidth - this._colReservedWidths;

        if (this._numColumns === 4) {
            contentWidth /= 2;
        }

        /* Calculate the desired widths of the filename columns. */
        let filenameWidth = fullWidth - this._filenameReservedWidths;

        if (this._numFilenameColumns === 2) {
            filenameWidth /= 2;
        }

        this.$el.width(fullWidth);

        /* Update the minimum and maximum widths, if they've changed. */
        if (filenameWidth !== this._prevFilenameWidth) {
            this._$filenameRow.children('th').css({
                'min-width': Math.ceil(filenameWidth * 0.66),
                'max-width': Math.ceil(filenameWidth)
            });
            this._prevFilenameWidth = filenameWidth;
        }

        if (contentWidth !== this._prevContentWidth) {
            this._$revisionRow.children('.revision-col').css({
                'min-width': Math.ceil(contentWidth * 0.66),
                'max-width': Math.ceil(contentWidth)
            });
            this._prevContentWidth = contentWidth;
        }
    },

    /**
     * Handle a window resize.
     *
     * This will update the sizes of the diff columns, and the location of the
     * collapse buttons (if one or more are visible).
     */
    updateLayout() {
        this._updateColumnSizes();
        this._updateCollapseButtonPos();
    },

    /**
     * Handle a file download link being clicked.
     *
     * Prevents the event from bubbling up and being caught by
     * _onFileHeaderClicked.
     *
     * Args:
     *     e (jQuery.Event):
     *         The ``click`` event that triggered this handler.
     */
    _onDownloadLinkClicked(e) {
        e.stopPropagation();
    },

    /**
     * Handle the file header being clicked.
     *
     * This will highlight the file header.
     *
     * Args:
     *     e (jQuery.Event):
     *         The ``click`` event that triggered this handler.
     */
    _onFileHeaderClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this.trigger('fileClicked');
    },

    /**
     * Handle a "Moved to/from" flag being clicked.
     *
     * This will scroll to the location on the other end of the move,
     * and briefly highlight the line.
     *
     * Args:
     *     e (jQuery.Event):
     *         The ``click`` event that triggered this handler.
     */
    _onMovedLineClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this.trigger('moveFlagClicked', $(e.target).data('line'));
    },

    /**
     * Handle a mouse up event.
     *
     * This will select any chunk that was clicked, highlight the chunk,
     * and ensure it's cleanly scrolled into view.
     *
     * Args:
     *     e (jQuery.Event):
     *         The ``mouseup`` event that triggered this handler.
     */
    _onMouseUp(e) {
        const node = e.target;

        /*
         * The user clicked somewhere else. Move the anchor point here
         * if it's part of the diff.
         */
        const $tbody = $(node).closest('tbody');

        if ($tbody.length > 0 &&
            ($tbody.hasClass('delete') ||
             $tbody.hasClass('insert') ||
             $tbody.hasClass('replace'))) {
            const anchor = $tbody[0].querySelector('a');

            if (anchor) {
                this.trigger('chunkClicked', anchor.name);
            }
        }
    },

    /**
     * Handle an expand chunk button being clicked.
     *
     * The expand buttons will expand a collapsed chunk, either entirely
     * or by certain amounts. It will fetch the new chunk contents and
     * inject it into the diff viewer.
     *
     * Args:
     *     e (jQuery.Event):
     *         The ``click`` event that triggered this handler.
     */
    _onExpandChunkClicked(e) {
        e.preventDefault();

        let $target = $(e.target);

        if (!$target.hasClass('diff-expand-btn')) {
            /* We clicked an image inside the link. Find the parent. */
            $target = $target.closest('.diff-expand-btn');
        }

        this._expandOrCollapse($target, true);
    },

    /**
     * Handle a collapse chunk button being clicked.
     *
     * The fully collapsed representation of that chunk will be fetched
     * and put into the diff viewer in place of the expanded chunk.
     *
     * Args:
     *     e (jQuery.Event):
     *         The ``click`` event that triggered this handler.
     */
    _onCollapseChunkClicked(e) {
        e.preventDefault();

        let $target = $(e.target);

        if (!$target.hasClass('diff-collapse-btn')) {
            /* We clicked an image inside the link. Find the parent. */
            $target = $target.closest('.diff-collapse-btn');
        }

        this._expandOrCollapse($target, false);
    },

    /**
     * Handler for when show content is clicked.
     *
     * This requeues the corresponding diff to show its deleted content.
     *
     * Args:
     *     e (jQuery.Event):
     *         The ``click`` event that triggered this handler.
     */
    _onShowDeletedClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        /*
         * Replace the current contents ("This file was deleted ... ") with a
         * spinner. This will be automatically replaced with the file contents
         * once loaded from the server.
         */
        $(e.target).parent()
            .html('<span class="fa fa-spinner fa-pulse"></span>');

        this.trigger('showDeletedClicked');
    },
});
