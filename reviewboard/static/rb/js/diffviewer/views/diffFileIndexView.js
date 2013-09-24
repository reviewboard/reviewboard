/*
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

    events: {
        'click a': '_onAnchorClicked'
    },

    /*
     * Initializes the view.
     */
    initialize: function() {
        this._$items = null;
        this._$itemsTable = null;
        this._iconInsertColor = null;
        this._iconReplaceColor = null;
        this._iconDeleteColor = null;

        this.collection = this.options.collection;
        this.listenTo(this.collection, 'update', this.update);
    },

    /*
     * Renders the view to the page.
     *
     * This will grab the list of items and precompute the colors used in
     * the complexity icons.
     */
    render: function() {
        var $iconColor = $('<div/>').appendTo(document.body);

        this._$itemsTable = $('<table/>').appendTo(this.el);
        this._$items = this.$('tr');

        $iconColor[0].className = 'diff-changes-icon-insert';
        this._iconInsertColor = $iconColor.css('color');

        $iconColor[0].className = 'diff-changes-icon-replace';
        this._iconReplaceColor = $iconColor.css('color');

        $iconColor[0].className = 'diff-changes-icon-delete';
        this._iconDeleteColor = $iconColor.css('color');

        $iconColor.remove();

        // Add the files from the collection
        this.update();

        return this;
    },

    _itemTemplate: _.template([
        '<tr class="loading<%',
        ' if (newfile) { print(" new-file"); }',
        ' if (binary) { print(" binary-file"); }',
        ' if (deleted) { print(" deleted-file"); }',
        ' if (destFilename !== depotFilename) { print(" renamed-file"); }',
        ' %>">',
        ' <td class="diff-file-icon"></td>',
        ' <td class="diff-file-info">',
        '  <a href="#<%- index %>"><%- destFilename %></a>',
        '  <% if (destFilename !== depotFilename) { %>',
        '  <span class="diff-file-rename"><%- wasText %></span>',
        '  <% } %>',
        ' </td>',
        ' <td class="diff-chunks-cell">',
        '  <% if (binary) { %>',
        '   <%- binaryFileText %>',
        '  <% } else if (deleted) { %>',
        '   <%- deletedFileText %>',
        '  <% } else { %>',
        '   <div class="diff-chunks"></div>',
        '  <% } %>',
        ' </td>',
        '</tr>'
    ].join('')),

    /*
     * Update the list of files in the index view.
     */
    update: function() {
        this._$itemsTable.empty();

        this.collection.each(function(file) {
            this._$itemsTable.append(this._itemTemplate(
                _.defaults({
                    binaryFileText: gettext('Binary file'),
                    deletedFileText: gettext('Deleted'),
                    wasText: interpolate(gettext('Was %s'),
                                         [file.get('depotFilename')])
                }, file.attributes)
            ));
        }, this);
        this._$items = this.$('tr');
    },

    /*
     * Adds a loaded diff to the index.
     *
     * The reserved entry for the diff will be populated with a link to the
     * diff, and information about the diff.
     */
    addDiff: function(index, diffReviewableView) {
        var $item = $(this._$items[index])
            .removeClass('loading');

        if (diffReviewableView.$el.hasClass('diff-error')) {
            this._renderDiffError($item);
        } else {
            this._renderDiffEntry($item, diffReviewableView);
        }
    },

    /*
     * Renders a diff loading error.
     *
     * An error icon will be displayed in place of the typical complexity
     * icon.
     */
    _renderDiffError: function($item) {
        $('<div class="rb-icon rb-icon-warning"/>')
            .appendTo($item.find('.diff-file-icon'));
    },

    /*
     * Renders the display of a loaded diff.
     */
    _renderDiffEntry: function($item, diffReviewableView) {
        var $table = diffReviewableView.$el,
            fileDeleted = $item.hasClass('deleted-file'),
            fileAdded = $item.hasClass('new-file'),
            linesEqual = $table.data('lines-equal'),
            numDeletes = 0,
            numInserts = 0,
            numReplaces = 0,
            chunksList = [];

        if (fileAdded) {
            numInserts = 1;
        } else if (fileDeleted) {
            numDeletes = 1;
        } else if ($item.hasClass('binary-file')) {
            numReplaces = 1;
        } else {
            _.each($table.children('tbody'), function(chunk) {
                var numRows = chunk.rows.length,
                    $chunk = $(chunk);

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
                    className: chunk.className
                }));
            }, this);

            /* Add clickable blocks for each diff chunk. */
            $item.find('.diff-chunks').html(chunksList.join(''));
        }

        /* Render the complexity icon. */
        this._renderComplexityIcon($item, numInserts, numDeletes, numReplaces,
                                   linesEqual + numDeletes + numInserts +
                                   numReplaces);

        this.listenTo(diffReviewableView, 'chunkDimmed chunkUndimmed',
                      function(chunkID) {
            this.$('a[href="#' + chunkID + '"]').toggleClass('dimmed');
        });
    },

    /*
     * Renders the icon showing the general complexity of the diff.
     *
     * This icon is a pie graph showing the percentage of adds vs deletes
     * vs replaces. The size of the white inner radius is a relative indicator
     * of how large the change is for the file. Smaller inner radiuses indicate
     * much larger changes, whereas larger radiuses represent smaller changes.
     *
     * Think of the inner radius as the unchanged lines.
     */
    _renderComplexityIcon: function($item, numInserts, numDeletes, numReplaces,
                                    totalLines) {
        function clampValue(val) {
            return val === 0 ? 0 : Math.max(val, minValue);
        }

        var numTotal = numInserts + numDeletes + numReplaces,
            minValue = numTotal * 0.15;

        $('<div/>')
            .width(20)
            .height(20)
            .appendTo($item.find('.diff-file-icon'))
            .plot(
                [
                    {
                        color: this._iconInsertColor,
                        data: clampValue(numInserts)
                    },
                    {
                        color: this._iconDeleteColor,
                        data: clampValue(numDeletes)
                    },
                    {
                        color: this._iconReplaceColor,
                        data: clampValue(numReplaces)
                    }
                ],
                {
                    series: {
                        pie: {
                            show: true,
                            innerRadius: 0.5 *
                                         ((totalLines - numTotal) / totalLines),
                            radius: 0.8
                        }
                    }
                }
            );
    },

    /*
     * Handler for when an anchor is clicked.
     *
     * Gets the name of the target and emits anchorClicked.
     */
    _onAnchorClicked: function(e) {
        e.preventDefault();

        this.trigger('anchorClicked', e.target.href.split('#')[1]);
    }
});
