/**
 * A view for the diff file index.
 */
import { BaseView, EventsHash, spina } from '@beanbag/spina';

import { DiffComplexityIconView } from './diffComplexityIconView';


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

    static events: EventsHash = {
        'click a': '_onAnchorClicked',
    };

    /**********************
     * Instance variables *
     **********************/
    #$items: JQuery = null;
    #$itemsTable: JQuery = null;

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
     * Render the view to the page.
     */
    onInitialRender() {
        // Remove the spinner.
        this.$el.empty();

        this.#$itemsTable = $('<table/>').appendTo(this.$el);
        this.#$items = this.$('tr');

        // Add the files from the collection.
        this.#update();
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
}
