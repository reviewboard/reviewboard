/**
 * Displays the file index for the diffs on a page.
 *
 * The file page lists the names of the files, as well as a little graph
 * icon showing the relative size and complexity of a file, a list of chunks
 * (and their types), and the number of lines added and removed.
 */
RB.DiffFileIndexView = Backbone.View.extend({
    chunkTemplate: _.template(
        '<a href="#<%= chunkID %>" class="<%= className %>"> </a>'
    ),

    _itemTemplate: _.template(dedent`
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
    `),

    events: {
        'click a': '_onAnchorClicked',
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     collection (RB.DiffFileCollection):
     *         The collection containing the files.
     */
    initialize(options) {
        this.options = options;
        this._$items = null;
        this._$itemsTable = null;

        this.collection = this.options.collection;
        this.listenTo(this.collection, 'reset update', this.update);
    },

    /**
     * Render the view to the page.
     *
     * Returns:
     *     RB.DiffFileIndexView:
     *     This object, for chaining.
     */
    render() {
        this.$el.empty();

        this._$itemsTable = $('<table/>').appendTo(this.$el);
        this._$items = this.$('tr');

        // Add the files from the collection
        this.update();

        return this;
    },

    /**
     * Update the list of files in the index view.
     */
    update() {
        this._$itemsTable.empty();

        this.collection.each(file => {
            this._$itemsTable.append(this._itemTemplate(
                _.defaults({
                    binaryFileText: gettext('Binary file'),
                    deletedFileText: gettext('Deleted'),
                    wasText: interpolate(gettext('Was %s'),
                                         [file.get('depotFilename')]),
                }, file.attributes)
            ));
        });

        this._$items = this.$('tr');
    },

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
    addDiff(index, diffReviewableView) {
        const $item = $(this._$items[index])
            .removeClass('loading');

        if (diffReviewableView.$el.hasClass('diff-error')) {
            this._renderDiffError($item);
        } else {
            this._renderDiffEntry($item, diffReviewableView);
        }
    },

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
    _renderDiffError($item) {
        $item.find('.diff-file-icon')
            .html('<div class="rb-icon rb-icon-warning" />')
            .attr('title',
                  gettext('There was an error loading this diff. See the details below.'));
    },

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
    _renderDiffEntry($item, diffReviewableView) {
        const $table = diffReviewableView.$el;
        const fileDeleted = $item.hasClass('deleted-file');
        const fileAdded = $item.hasClass('new-file');
        const linesEqual = $table.data('lines-equal');
        let numDeletes = 0;
        let numInserts = 0;
        let numReplaces = 0;
        let tooltip = '';
        const tooltipParts = [];
        const chunksList = [];

        if (fileAdded) {
            numInserts = 1;
        } else if (fileDeleted) {
            numDeletes = 1;
        } else if ($item.hasClass('binary-file')) {
            numReplaces = 1;
        } else {
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

                chunksList.push(this.chunkTemplate({
                    chunkID: chunk.id.substr(5),
                    className: chunk.className,
                }));
            });

            /* Add clickable blocks for each diff chunk. */
            $item.find('.diff-chunks').html(chunksList.join(''));
        }

        /* Render the complexity icon. */
        const iconView = new RB.DiffComplexityIconView({
            numInserts: numInserts,
            numDeletes: numDeletes,
            numReplaces: numReplaces,
            totalLines: linesEqual + numDeletes + numInserts + numReplaces,
        });

        const $fileIcon = $item.find('.diff-file-icon');
        $fileIcon
            .empty()
            .append(iconView.$el);

        iconView.render();

        /* Add tooltip for icon */
        if (fileAdded) {
            tooltip = gettext('New file');
        } else if (fileDeleted) {
            tooltip = gettext('Deleted file');
        } else {
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

        $fileIcon.attr('title', tooltip);

        this.listenTo(
            diffReviewableView,
            'chunkDimmed chunkUndimmed',
            chunkID => {
                this.$(`a[href="#${chunkID}"]`).toggleClass('dimmed');
            });
    },

    /**
     * Handler for when an anchor is clicked.
     *
     * Gets the name of the target and emits anchorClicked.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    _onAnchorClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this.trigger('anchorClicked', e.target.href.split('#')[1]);
    },
});
