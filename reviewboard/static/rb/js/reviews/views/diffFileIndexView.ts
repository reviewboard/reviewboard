/**
 * A view for the diff file index.
 */
import { BaseView, EventsHash, spina } from '@beanbag/spina';

import { EnabledFeatures } from 'reviewboard/common';

import { DiffComplexityIconView } from './diffComplexityIconView';
import { UnifiedBannerView } from './unifiedBannerView';


/**
 * Options for the DiffFileIndexView.
 *
 * Version Added:
 *     6.0
 */
interface DiffFileIndexViewOptions {
    /** The collection of DiffFile models. */
    collection: Backbone.Collection;
}


/**
 * Storage for the extents of an element when scroll tracking.
 */
interface ScrollExtents {
    /** The top of the element. */
    top: number;

    /** The height of the element. */
    height: number;

    /** The bottom of the element. */
    bottom: number;
}


/**
 * Displays the file index for the diffs on a page.
 *
 * The file page lists the names of the files, as well as a little graph
 * icon showing the relative size and complexity of a file, a list of chunks
 * (and their types), and the number of lines added and removed.
 */
@spina
export class DiffFileIndexView extends BaseView<
    undefined,
    HTMLDivElement,
    DiffFileIndexViewOptions
> {
    static chunkTemplate = _.template(
        '<a href="#<%= chunkID %>" class="<%= className %>"> </a>'
    );

    static itemTemplate = _.template(dedent`
        <tr class="loading
         <% if (newfile) { %>new-file<% } %>
         <% if (binary) { %>binary-file<% } %>
         <% if (deleted) { %>deleted-file<% } %>
         <% if (destFilename !== depotFilename) { %>renamed-file<% } %>
         ">
         <td class="diff-file-icon">
          <span class="fa fa-spinner fa-pulse"></span>
         </td>
         <td class="diff-file-info">
          <a href="#<%- index %>"><%- destFilename %></a>
          <% if (destFilename !== depotFilename) { %>
          <span class="diff-file-rename"><%- wasText %></span>
          <% } %>
         </td>
         <td class="diff-chunks-cell">
          <% if (binary) { %>
           <%- binaryFileText %>
          <% } else if (deleted) { %>
           <%- deletedFileText %>
          <% } else { %>
           <div class="diff-chunks"></div>
          <% } %>
         </td>
        </tr>
    `);

    static dockTemplate = `
        <div class="rb-c-diff-file-index-dock">
         <div class="rb-c-diff-file-index-dock__table"></div>
        </div>
    `;

    static events: EventsHash = {
        'click a': '_onAnchorClicked',
    };

    /**********************
     * Instance variables *
     **********************/

    #diffFiles = new Map<number, JQuery>();
    #isDocked = false;
    #unifiedBannerView: UnifiedBannerView;
    #$bannerDock: JQuery = null;
    #$dockContainer: JQuery = null;
    #$dockTable: JQuery = null;
    #$floatSpacer: JQuery = null;
    #$items: JQuery = null;
    #$itemsTable: JQuery = null;

    #indexExtents = new Map<number, ScrollExtents>();
    #diffExtents = new Map<number, ScrollExtents>();

    /**
     * Initialize the view.
     *
     * Args:
     *     options (DiffFileIndexViewOptions):
     *         Options for the view.
     */
    initialize(options: DiffFileIndexViewOptions) {
        this.collection = options.collection;
        this.listenTo(this.collection, 'reset update', this.#update);
    }

    /**
     * Remove the view from the DOM.
     *
     * Returns:
     *     DiffFileIndexView:
     *     This object, for chaining.
     */
    remove(): this {
        $(window).off(`scroll.${this.cid}`);

        if (this.#$floatSpacer !== null) {
            this.#$floatSpacer.remove();
            this.#$floatSpacer = null;
        }

        if (this.#$dockContainer !== null) {
            this.#$dockContainer.remove();
            this.#$dockContainer = null;
        }

        this.#$bannerDock = null;
        this.#$dockTable = null;
        this.#$items = null;
        this.#$itemsTable = null;

        this.#indexExtents.clear();
        this.#diffExtents.clear();

        return super.remove();
    }

    /**
     * Render the view to the page.
     */
    onInitialRender() {
        // Remove the spinner.
        this.$el.empty();

        this.#$itemsTable = $('<table class="rb-c-diff-file-index">')
            .appendTo(this.$el);
        this.#$items = this.$('tr');

        this.#unifiedBannerView = UnifiedBannerView.getInstance();

        /*
         * Check both the feature and whether the banner exists, because it's
         * possible that it's not instantiated during some unit tests.
         */
        if (EnabledFeatures.unifiedBanner &&
            this.#unifiedBannerView !== null) {
            this.#$bannerDock = this.#unifiedBannerView.getDock();

            this.#$dockContainer = $(DiffFileIndexView.dockTemplate);
            this.#$dockTable = this.#$dockContainer
                .children('.rb-c-diff-file-index-dock__table');

            $(window).on(`scroll.${this.cid}`,
                         () => this.#updateFloatPosition());
            _.defer(() => this.#updateFloatPosition());
        }

        // Add the files from the collection
        this.#update();
    }

    /**
     * Clear the loaded diffs.
     */
    clear() {
        this.#diffFiles.clear();
        this.#diffExtents.clear();
        this.#indexExtents.clear();
    }

    /**
     * Add a loaded diff to the index.
     *
     * The reserved entry for the diff will be populated with a link to the
     * diff, and information about the diff.
     *
     * Args:
     *     index (number):
     *         The array index at which to add the new diff.
     *
     *     diffReviewableView (RB.DiffReviewableView):
     *         The view corresponding to the diff file being added.
     */
    addDiff(
        index: number,
        diffReviewableView: RB.DiffReviewableView,
    ) {
        const $item = $(this.#$items[index])
            .removeClass('loading');

        if (diffReviewableView.$el.hasClass('diff-error')) {
            this.#renderDiffError($item);
        } else {
            this.#renderDiffEntry($item, diffReviewableView);
        }

        this.#diffFiles.set(index, $(diffReviewableView.el));

        if (this.#isDocked) {
            this.updateLayout();
            this.#updateItemVisibility();
        }
    }

    /**
     * Update the list of files in the index view.
     */
    #update() {
        this.#$itemsTable.empty();

        this.collection.each(file => {
            this.#$itemsTable.append(DiffFileIndexView.itemTemplate(
                _.defaults({
                    binaryFileText: _`Binary file`,
                    deletedFileText: _`Deleted`,
                    wasText: interpolate(_`Was %s`,
                                         [file.get('depotFilename')]),
                }, file.attributes)
            ));
        });

        this.#$items = this.$('tr');
    }

    /**
     * Render a diff loading error.
     *
     * An error icon will be displayed in place of the typical complexity
     * icon.
     *
     * Args:
     *     $item (jQuery):
     *         The item in the file index which encountered the error.
     */
    #renderDiffError($item: JQuery) {
        $item.find('.diff-file-icon')
            .html('<div class="rb-icon rb-icon-warning" />')
            .attr('title',
                  _`There was an error loading this diff. See the details below.`);
    }

    /**
     * Render the display of a loaded diff.
     *
     * Args:
     *     $item (jQuery):
     *         The item in the file index which was loaded.
     *
     *     diffReviewableView (RB.DiffReviewableView):
     *         The view corresponding to the diff file which was loaded.
     */
    #renderDiffEntry(
        $item: JQuery,
        diffReviewableView: RB.DiffReviewableView,
    ) {
        const $table = diffReviewableView.$el;
        const fileDeleted = $item.hasClass('deleted-file');
        const fileAdded = $item.hasClass('new-file');
        const linesEqual = $table.data('lines-equal');
        let numDeletes = 0;
        let numInserts = 0;
        let numReplaces = 0;
        let tooltip = '';

        if (fileAdded) {
            numInserts = 1;
        } else if (fileDeleted) {
            numDeletes = 1;
        } else if ($item.hasClass('binary-file')) {
            numReplaces = 1;
        } else {
            const chunksList: string[] = [];

            $table.children('tbody').each((i, chunk) => {
                const numRows = chunk.rows.length;
                const $chunk = $(chunk);

                if ($chunk.hasClass('delete')) {
                    numDeletes += numRows;
                } else if ($chunk.hasClass('insert')) {
                    numInserts += numRows;
                } else if ($chunk.hasClass('replace')) {
                    numReplaces += numRows;
                } else {
                    return;
                }

                chunksList.push(DiffFileIndexView.chunkTemplate({
                    chunkID: chunk.id.substr(5),
                    className: chunk.className,
                }));
            });

            /* Add clickable blocks for each diff chunk. */
            $item.find('.diff-chunks').html(chunksList.join(''));
        }

        /* Render the complexity icon. */
        const iconView = new DiffComplexityIconView({
            numDeletes: numDeletes,
            numInserts: numInserts,
            numReplaces: numReplaces,
            totalLines: linesEqual + numDeletes + numInserts + numReplaces,
        });

        /* Add tooltip for icon */
        if (fileAdded) {
            tooltip = _`New file`;
        } else if (fileDeleted) {
            tooltip = _`Deleted file`;
        } else {
            const tooltipParts: string[] = [];

            if (numInserts > 0) {
                tooltipParts.push(interpolate(
                    ngettext('%s new line', '%s new lines', numInserts),
                    [numInserts]));
            }

            if (numReplaces > 0) {
                tooltipParts.push(interpolate(
                    ngettext('%s line changed', '%s lines changed', numReplaces),
                    [numReplaces]));
            }

            if (numDeletes > 0) {
                tooltipParts.push(interpolate(
                    ngettext('%s line removed', '%s lines removed', numDeletes),
                    [numDeletes]));
            }

            tooltip = tooltipParts.join(', ');
        }

        $item.find('.diff-file-icon')
            .empty()
            .append(iconView.$el)
            .attr('title', tooltip);

        iconView.render();

        this.listenTo(
            diffReviewableView,
            'chunkDimmed chunkUndimmed',
            chunkID => {
                this.$(`a[href="#${chunkID}"]`).toggleClass('dimmed');
            });
    }

    /**
     * Handler for when an anchor is clicked.
     *
     * Gets the name of the target and emits anchorClicked.
     *
     * Args:
     *     e (MouseEvent):
     *         The click event.
     */
    private _onAnchorClicked(e: MouseEvent) {
        e.preventDefault();
        e.stopPropagation();

        const target = e.target as HTMLAnchorElement;
        this.trigger('anchorClicked', target.href.split('#')[1]);
    }

    /**
     * Update the position of the file index.
     *
     * If the unified banner is available, this will dock the file index into
     * the banner once it's scrolled past.
     */
    #updateFloatPosition() {
        if (this.$el.parent().length === 0) {
            return;
        }

        if (this.#$floatSpacer === null) {
            this.#$floatSpacer = this.$el.wrap($('<div>')).parent();
        }

        const bannerTop = this.#$bannerDock.offset().top;
        const indexHeight = this.#$itemsTable.outerHeight(true);
        const topOffset = this.#$floatSpacer.offset().top - bannerTop;
        const lastRowHeight = this.#$itemsTable.children().last()
            .outerHeight(true);

        if (!this.#isDocked &&
            topOffset + indexHeight - lastRowHeight < 0) {
            /* Transition from undocked -> docked */
            this.$el.addClass('-is-docked');
            this.#isDocked = true;
            this.#$dockContainer.appendTo(this.#$bannerDock);
            this.#$dockTable.append(this.#$itemsTable);
            this.#$floatSpacer.height(indexHeight);

            this.updateLayout();
            this.#updateItemVisibility();
        } else if (this.#isDocked &&
                   topOffset + indexHeight - lastRowHeight >= 0) {
            /* Transition from docked -> undocked. */
            this.#$floatSpacer.css('height', '');

            this.$el.removeClass('-is-docked');

            this.#$itemsTable
                .css('transform', 'inherit')
                .appendTo(this.$el);
            this.#$dockContainer.detach();
            this.#isDocked = false;
            this.#$items.show();
        } else if (this.#isDocked) {
            /* Currently docked. Update index scroll. */
            this.#updateItemVisibility();
        }
    }

    /**
     * Update the stored sizes for the file index and diff entries.
     */
    updateLayout() {
        function getExtents(
            $el: JQuery,
        ): ScrollExtents {
            const height = $el.outerHeight();
            const top = $el.offset().top;
            const bottom = top + height;

            return {
                bottom,
                height,
                top,
            };
        }

        if (this.#isDocked === true) {
            this.#indexExtents.clear();
            this.#diffExtents.clear();

            const indexListTop = this.#$itemsTable.offset().top;
            const $items = this.#$items;
            const indexExtents = this.#indexExtents;
            const diffExtents = this.#diffExtents;

            for (const [i, $diffEl] of this.#diffFiles.entries()) {
                const $indexEl = $items.eq(i);

                const indexHeight = $indexEl.outerHeight();
                const indexTop = $indexEl.offset().top - indexListTop;
                const indexBottom = indexTop + indexHeight;

                indexExtents.set(i, {
                    bottom: indexBottom,
                    height: indexHeight,
                    top: indexTop,
                });
                diffExtents.set(i, getExtents($diffEl));
            }
        }

        if (this.#isDocked) {
            this.#updateItemVisibility();
        }
    }

    /**
     * Update the visibility state of the (docked) file list.
     *
     * When the file list is in docked mode, we carefully manage its vertical
     * offset and height in order to keep it in sync with which files are
     * visible on the screen.
     */
    #updateItemVisibility() {
        const $window = $(window);
        const viewportTop = this.#$dockContainer.offset().top;
        const viewportBottom = $window.scrollTop() + $window.height();
        const buffer = 50; // 50px

        let verticalOffset = undefined;
        let listHeight = 0;
        let fullLastEntry = true;

        const diffExtents = this.#diffExtents;
        const indexExtents = this.#indexExtents;

        for (let i = 0; i < this.#$items.length; i++) {
            const diffExtent = diffExtents.get(i);
            const indexExtent = indexExtents.get(i);

            if (diffExtent === undefined) {
                /*
                 * We may be trying to load an anchor prior to all the diffs
                 * being fully loaded.
                 */
                continue;
            }

            if (diffExtent.bottom < viewportTop) {
                // This entry is entirely above the visible viewport.
                continue;
            } else if (diffExtent.top > viewportBottom) {
                // This entry is below the visible viewport. We can bail now.
                break;
            }

            if (diffExtent.bottom < viewportTop + buffer) {
                /*
                 * The bottom of the diff entry is in the process of being
                 * scrolled off (or onto) the screen. Scroll the index
                 * entry to match.
                 */
                const ratio = (diffExtent.bottom - viewportTop) / buffer;
                const visibleArea = ratio * indexExtent.height;
                verticalOffset = indexExtent.bottom - visibleArea;
                listHeight += visibleArea;
            } else if (diffExtent.top > viewportBottom - buffer) {
                /*
                 * The top of the diff entry is in the process of being
                 * scrolled off (or onto) the screen. Scroll the index
                 * entry to match.
                 */
                const ratio = (viewportBottom - diffExtent.top) / buffer;
                const visibleArea = ratio * indexExtent.height;
                listHeight += visibleArea;

                fullLastEntry = false;
            } else {
                if (verticalOffset === undefined) {
                    verticalOffset = indexExtent.top;

                    if (verticalOffset > 0) {
                        // Account for the border between <tr> elements.
                        verticalOffset += 1;
                    }
                }

                listHeight += indexExtent.height;
            }
        }

        window.requestAnimationFrame(() => {
            if (fullLastEntry) {
                // Account for the border between <tr> elements.
                listHeight -= 1;
            }

            this.#$dockTable.height(listHeight);
            this.#$itemsTable.css('transform',
                                  `translateY(-${verticalOffset}px)`);
        });
    }
}
