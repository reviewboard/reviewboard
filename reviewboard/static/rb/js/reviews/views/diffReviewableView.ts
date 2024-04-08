/**
 * Handles reviews of the diff for a file.
 */

import {
    type EventsHash,
    spina,
} from '@beanbag/spina';

import { CenteredElementManager } from 'reviewboard/ui';

import { type DiffReviewable } from '../models/diffReviewableModel';
import { AbstractReviewableView } from './abstractReviewableView';
import { DiffCommentBlockView } from './diffCommentBlockView';
import { TextCommentRowSelector } from './textCommentRowSelectorView';


/**
 * Handles reviews of the diff for a file.
 *
 * This provides commenting abilities for ranges of lines on a diff, as well
 * as showing existing comments, and handling other interaction around
 * per-file diffs.
 */
@spina
export class DiffReviewableView extends AbstractReviewableView<
    DiffReviewable, HTMLTableElement> {
    static tagName = 'table';

    static commentBlockView = DiffCommentBlockView;
    static commentsListName = 'diff_comments';

    static events: EventsHash = {
        'click .diff-expand-btn': '_onExpandChunkClicked',
        'click .download-link': '_onDownloadLinkClicked',
        'click .moved-to, .moved-from': '_onMovedLineClicked',
        'click .rb-c-diff-collapse-button': '_onCollapseChunkClicked',
        'click .rb-o-toggle-ducs': '_onToggleUnicodeCharsClicked',
        'click .show-deleted-content-action': '_onShowDeletedClicked',
        'click thead tr': '_onFileHeaderClicked',
        'mouseup': '_onMouseUp',
    };

    /**********************
     * Instance variables *
     **********************/

    /**
     * The manager for centering various controls.
     *
     * This is public for consupmtion in unit tests.
     */
    _centered: CenteredElementManager;

    /**
     * The row selector object.
     *
     * This is public for consupmtion in unit tests.
     */
    _selector: TextCommentRowSelector;

    /** The row containing the filename(s). */
    #$filenameRow: JQuery<HTMLTableRowElement> = null;

    /** The parent element for the view. */
    #$parent: JQuery;

    /** The row containing the file revisions. */
    #$revisionRow: JQuery<HTMLTableRowElement> = null;

    /** The wrapped window object. */
    #$window: JQuery<Window> = $(window);

    /** The reserved widths for the content columns. */
    #colReservedWidths = 0;

    /** The reserved widths for the filename columns. */
    #filenameReservedWidths = 0;

    /** The comment blocks which are currently hidden in collapsed lines. */
    #hiddenCommentBlockViews: DiffCommentBlockView[] = [];

    /** The number of columns in the table. */
    #numColumns = 0;

    /** The number of filename columns in the table. */
    #numFilenameColumns = 0;

    /** The saved content column width of the table. */
    #prevContentWidth = 0;

    /** The saved filename column width of the table. */
    #prevFilenameWidth = 0;

    /** The saved full width of the table. */
    #prevFullWidth = 0;

    /** The comment blocks which are currently visible. */
    #visibleCommentBlockViews: DiffCommentBlockView[] = [];

    /**
     * Initialize the reviewable for a file's diff.
     */
    initialize() {
        super.initialize();

        this._selector = new TextCommentRowSelector({
            el: this.el,
            reviewableView: this,
        });

        /*
         * Wrap this only once so we don't have to re-wrap every time
         * the page scrolls.
         */
        this.#$parent = this.$el.parent();

        this.on('commentBlockViewAdded', this._placeCommentBlockView, this);
    }

    /**
     * Remove the reviewable from the DOM.
     *
     * Returns:
     *     DiffReviewableView:
     *     This object, for chaining.
     */
    remove(): this {
        this._selector.remove();

        return super.remove();
    }

    /**
     * Render the reviewable.
     */
    onInitialRender() {
        super.onInitialRender();

        this._centered = new CenteredElementManager();

        const $thead = $(this.el.tHead);

        this.#$revisionRow = $thead.children('.revision-row') as
            JQuery<HTMLTableRowElement>;
        this.#$filenameRow = $thead.children('.filename-row') as
            JQuery<HTMLTableRowElement>;

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
    }

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
    }

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
    createComment(
        beginLineNum: number,
        endLineNum: number,
        beginNode: HTMLElement,
        endNode: HTMLElement,
    ) {
        this._selector.createComment(beginLineNum, endLineNum, beginNode,
                                     endNode);
    }

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
     *
     * Returns:
     *     number:
     *     The row index where the comment block was placed.
     */
    _placeCommentBlockView(
        commentBlockView: DiffCommentBlockView,
        prevBeginRowIndex: number,
    ): number {
        const commentBlock = commentBlockView.model;

        const rowEls = this._selector.getRowsForRange(
            commentBlock.get('beginLineNum'),
            commentBlock.get('endLineNum'),
            prevBeginRowIndex);

        if (rowEls !== null) {
            const beginRowEl = rowEls[0] as HTMLTableRowElement;
            const endRowEl = rowEls[1] as HTMLTableRowElement;

            /*
             * Note that endRow might be null if it exists in a collapsed
             * region, so we can get away with just using beginRow if we
             * need to.
             */
            commentBlockView.setRows($(beginRowEl), $(endRowEl || beginRowEl));
            commentBlockView.$el.appendTo(
                (commentBlockView.$beginRow as JQuery<HTMLTableRowElement>)[0]
                .cells[0]);
            this.#visibleCommentBlockViews.push(commentBlockView);

            return beginRowEl.rowIndex;
        } else {
            this.#hiddenCommentBlockViews.push(commentBlockView);

            return prevBeginRowIndex;
        }
    }

    /**
     * Place any hidden comment blocks onto the diff viewer.
     */
    _placeHiddenCommentBlockViews() {
        const hiddenCommentBlockViews = this.#hiddenCommentBlockViews;
        this.#hiddenCommentBlockViews = [];
        let prevBeginRowIndex;

        for (let i = 0; i < hiddenCommentBlockViews.length; i++) {
            prevBeginRowIndex = this._placeCommentBlockView(
                hiddenCommentBlockViews[i], prevBeginRowIndex);
        }
    }

    /**
     * Mark any comment block views not visible as hidden.
     */
    _hideRemovedCommentBlockViews() {
        const visibleCommentBlockViews = this.#visibleCommentBlockViews;
        this.#visibleCommentBlockViews = [];

        for (let i = 0; i < visibleCommentBlockViews.length; i++) {
            const commentBlockView = visibleCommentBlockViews[i];

            if (commentBlockView.$el.is(':visible')) {
                this.#visibleCommentBlockViews.push(commentBlockView);
            } else {
                this.#hiddenCommentBlockViews.push(commentBlockView);
            }
        }

        /* Sort these by line number so we can efficiently place them later. */
        _.sortBy(
            this.#hiddenCommentBlockViews,
            commentBlockView => commentBlockView.model.get('beginLineNum'));
    }

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
    }

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
    async _expandOrCollapse(
        $btn: JQuery,
        expanding: boolean,
    ) {
        const chunkIndex = $btn.data('chunk-index');
        const linesOfContext = $btn.data('lines-of-context');

        const html = await this.model.getRenderedDiffFragment({
            chunkIndex: chunkIndex,
            linesOfContext: linesOfContext,
        });

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
                                 this.#$window.scrollTop());

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

                this.#$window.scrollTop(
                    $scrollAnchor.offset().top - scrollOffsetTop);
            }
        }

        /* Recompute the set of buttons for later use. */
        this._centered.setElements(new Map(
            Array.prototype.map.call(
                this.$('.rb-c-diff-collapse-button'),
                el => {
                    const $tbody = $(el).closest('tbody');
                    const $prev = $tbody.prev();
                    const $next = $tbody.next();

                    return [el, {
                        $parent: $tbody,

                        /*
                         * Try to map the previous equals block, if available.
                         */
                        $top:
                            ($prev.length === 1 && $prev.hasClass('equal'))
                            ? $prev
                            : $tbody,

                        /* And now the next one. */
                        $bottom:
                            ($next.length === 1 && $next.hasClass('equal'))
                            ? $next
                            : $tbody,
                    }];
                })
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

    /**
     * Pre-calculate the widths and other state needed for column widths.
     *
     * This will store the number of columns and the reserved space that
     * needs to be subtracted from the container width, to be used in later
     * calculating the desired widths of the content areas.
     */
    _precalculateContentWidths() {
        let cellPadding = 0;

        if (!this.$el.hasClass('diff-error') &&
            this.#$revisionRow.length > 0) {
            const containerExtents = this.$el.getExtents('p', 'lr');

            /* Calculate the widths and state of the diff columns. */
            let $cells = $(this.#$revisionRow[0].cells);
            cellPadding = $(this.el.querySelector('pre'))
                .parent().addBack()
                .getExtents('p', 'lr');

            this.#colReservedWidths = $cells.eq(0).outerWidth() + cellPadding +
                                      containerExtents;
            this.#numColumns = $cells.length;

            if (this.#numColumns === 4) {
                /* There's a left-hand side and a right-hand side. */
                this.#colReservedWidths += $cells.eq(2).outerWidth() +
                                           cellPadding;
            }

            /* Calculate the widths and state of the filename columns. */
            $cells = $(this.#$filenameRow[0].cells);
            this.#numFilenameColumns = $cells.length;
            this.#filenameReservedWidths = containerExtents +
                                           2 * this.#numFilenameColumns;
        } else {
            this.#colReservedWidths = 0;
            this.#filenameReservedWidths = 0;
            this.#numColumns = 0;
            this.#numFilenameColumns = 0;
        }
    }

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

        let $parent = this.#$parent;

        if (!$parent.is(':visible')) {
            /*
             * We're still in diff loading mode, and the parent is hidden. We
             * can get the width we need from the parent. It should be the
             * same, or at least close enough for the first stab at column
             * sizes.
             */
            $parent = $parent.parent();
        }

        const fullWidth = $parent.width();

        if (fullWidth === this.#prevFullWidth) {
            return;
        }

        this.#prevFullWidth = fullWidth;

        /* Calculate the desired widths of the diff columns. */
        let contentWidth = fullWidth - this.#colReservedWidths;

        if (this.#numColumns === 4) {
            contentWidth /= 2;
        }

        /* Calculate the desired widths of the filename columns. */
        let filenameWidth = fullWidth - this.#filenameReservedWidths;

        if (this.#numFilenameColumns === 2) {
            filenameWidth /= 2;
        }

        this.$el.width(fullWidth);

        /* Update the minimum and maximum widths, if they've changed. */
        if (filenameWidth !== this.#prevFilenameWidth) {
            this.#$filenameRow.children('th').css({
                'max-width': Math.ceil(filenameWidth),
                'min-width': Math.ceil(filenameWidth * 0.66),
            });
            this.#prevFilenameWidth = filenameWidth;
        }

        if (contentWidth !== this.#prevContentWidth) {
            this.#$revisionRow.children('.revision-col').css({
                'max-width': Math.ceil(contentWidth),
                'min-width': Math.ceil(contentWidth * 0.66),
            });
            this.#prevContentWidth = contentWidth;
        }
    }

    /**
     * Handle a window resize.
     *
     * This will update the sizes of the diff columns, and the location of the
     * collapse buttons (if one or more are visible).
     */
    updateLayout() {
        this._updateColumnSizes();
        this._updateCollapseButtonPos();
    }

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
    _onDownloadLinkClicked(e: Event) {
        e.stopPropagation();
    }

    /**
     * Handle the file header being clicked.
     *
     * This will highlight the file header.
     *
     * Args:
     *     e (jQuery.Event):
     *         The ``click`` event that triggered this handler.
     */
    _onFileHeaderClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        this.trigger('fileClicked');
    }

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
    _onMovedLineClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        this.trigger('moveFlagClicked', $(e.target).data('line'));
    }

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
    _onMouseUp(e: MouseEvent) {
        const node = e.target;

        /*
         * The user clicked somewhere else. Move the anchor point here
         * if it's part of the diff.
         */
        const $tbody = $(node).closest('tbody') as JQuery<HTMLElement>;

        if ($tbody.length > 0 &&
            ($tbody.hasClass('delete') ||
             $tbody.hasClass('insert') ||
             $tbody.hasClass('replace'))) {
            const anchor = $tbody[0].querySelector('a');

            if (anchor) {
                this.trigger('chunkClicked', anchor.name);
            }
        }
    }

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
    _onExpandChunkClicked(e: JQuery.TriggeredEvent) {
        e.preventDefault();

        this._expandOrCollapse($(e.currentTarget), true);
    }

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
    _onCollapseChunkClicked(e: JQuery.TriggeredEvent) {
        e.preventDefault();

        this._expandOrCollapse($(e.currentTarget), false);
    }

    /**
     * Handler for when show content is clicked.
     *
     * This requeues the corresponding diff to show its deleted content.
     *
     * Args:
     *     e (jQuery.Event):
     *         The ``click`` event that triggered this handler.
     */
    _onShowDeletedClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        /*
         * Replace the current contents ("This file was deleted ... ") with a
         * spinner. This will be automatically replaced with the file contents
         * once loaded from the server.
         */
        $(e.target).parent()
            .html('<span class="djblets-o-spinner"></span>');

        this.trigger('showDeletedClicked');
    }

    /**
     * Handler for the suspicious characters toggle button.
     *
     * This will toggle the ``-hide-ducs`` CSS class on the main element, and
     * toggle the show/hide text on the button that triggered this handler.
     *
     * Args:
     *     e (jQuery.Event):
     *         The ``click`` event that triggered this handler.
     */
    _onToggleUnicodeCharsClicked(e: Event) {
        const $el = this.$el;
        const $button = $(e.target);
        const ducsShown = !$el.hasClass('-hide-ducs');

        if (ducsShown) {
            $el.addClass('-hide-ducs');
            $button.text($button.data('show-chars-label'));
        } else {
            $el.removeClass('-hide-ducs');
            $button.text($button.data('hide-chars-label'));
        }
    }
}
