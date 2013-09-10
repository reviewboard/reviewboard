(function() {


var DiffFileIndexView;


/*
 * Displays the file index for the diffs on a page.
 *
 * The file page lists the names of the files, as well as a little graph
 * icon showing the relative size and complexity of a file, a list of chunks
 * (and their types), and the number of lines added and removed.
 */
DiffFileIndexView = Backbone.View.extend({
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
     *
     * `files` is a DiffFileCollection.
     */
    update: function(files) {
        this._$itemsTable.empty();

        files.each(function(file) {
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


/*
 * Manages the diff viewer page.
 *
 * This provides functionality for the diff viewer page for managing the
 * loading and display of diffs, and all navigation around the diffs.
 */
RB.DiffViewerPageView = RB.ReviewablePageView.extend({
    SCROLL_BACKWARD: -1,
    SCROLL_FORWARD: 1,

    ANCHOR_COMMENT: 1,
    ANCHOR_FILE: 2,
    ANCHOR_CHUNK: 4,

    DIFF_SCROLLDOWN_AMOUNT: 100,

    keyBindings: {
        'aAKP<m': '_selectPreviousFile',
        'fFJN>': '_selectNextFile',
        'sSkp,': '_selectPreviousDiff',
        'dDjn.': '_selectNextDiff',
        '[x': '_selectPreviousComment',
        ']c': '_selectNextComment',
        '\x0d': '_recenterSelected'
    },

    events: _.extend({
        'click .toggle-whitespace-only-chunks': '_toggleWhitespaceOnlyChunks',
        'click .toggle-show-whitespace': '_toggleShowExtraWhitespace'
    }, RB.ReviewablePageView.prototype.events),

    /*
     * Initializes the diff viewer page.
     */
    initialize: function() {
        var url;

        _.super(this).initialize.call(this);

        this._selectedAnchorIndex = -1;
        this._$anchors = $();
        this._$controls = null;
        this._diffReviewableViews = [];
        this._diffFileIndexView = null;

        /* Check to see if there's an anchor we need to scroll to. */
        url = document.location.toString();
        this._startAtAnchorName = (url.match('#') ? url.split('#')[1] : null);
    },

    /*
     * Removes the view from the page.
     */
    remove: function() {
        _.super(this).remove.call(this);

        this._diffFileIndexView.remove();
    },

    /*
     * Renders the page and begins loading all diffs.
     */
    render: function() {
        var $reviewRequest;

        _.super(this).render.call(this);

        $reviewRequest = this.$('.review-request');

        this._$controls = $reviewRequest.find('ul.controls');

        this._diffFileIndexView = new DiffFileIndexView({
            el: $('#diff_index')
        });
        this._diffFileIndexView
            .render()
            .update(this.options.files);

        this.listenTo(this._diffFileIndexView, 'anchorClicked',
                      this.selectAnchorByName);

        this._diffRevisionLabelView = new RB.DiffRevisionLabelView({
            el: $('#diff_revision_label'),
            model: this.options.revision
        });
        this._diffRevisionLabelView.render();

        this.listenTo(this._diffRevisionLabelView, 'revisionSelected',
                      this._onRevisionSelected);

        $('#diffs').bindClass(RB.UserSession.instance,
                              'diffsShowExtraWhitespace', 'ewhl');

        this._setFiles(this.options.files);

        return this;
    },

    _fileEntryTemplate: _.template([
        '<div class="diff-container">',
        ' <div class="diff-box">',
        '  <table class="sidebyside loading <% if (newfile) { %>newfile<% } %>"',
        '         id="file_container_<%- id %>">',
        '   <thead>',
        '    <tr class="filename-row">',
        '     <th colspan="2"><%- depotFilename %></th>',
        '    </tr>',
        '    <tr class="revision-row">',
        '    <th><%- revision %></th>',
        '    <th><%- destRevision %></th>',
        '    </tr>',
        '   </thead>',
        '   <tbody>',
        '    <tr><td colspan="2"><pre>&nbsp;</pre></td></tr>',
        '   </tbody>',
        '  </table>',
        ' </div>',
        '</div>'
    ].join('')),

    /*
     * Set the displayed files.
     *
     * This will replace the displayed files with a set of pending entries,
     * queue loads for each file, and start the queue.
     *
     * `files` is a DiffFileCollection
     */
    _setFiles: function(files) {
        var $diffs = $('#diffs').empty();

        files.each(function(file) {
            var filediff = file.get('filediff'),
                interfilediff = file.get('interfilediff');

            $diffs.append(this._fileEntryTemplate(file.attributes));

            this.queueLoadDiff(filediff.id,
                               filediff.revision,
                               interfilediff ? interfilediff.id : null,
                               interfilediff ? interfilediff.revision : null,
                               file.get('index'),
                               file.get('commentCounts'));
        }, this);

        $.funcQueue('diff_files').start();
    },

    /*
     * Queues loading of a diff.
     *
     * When the diff is loaded, it will be placed into the appropriate location
     * in the diff viewer. The anchors on the page will be rebuilt. This will
     * then trigger the loading of the next file.
     */
    queueLoadDiff: function(fileDiffID, fileDiffRevision,
                            interFileDiffID, interdiffRevision,
                            fileIndex, serializedCommentBlocks) {
        var diffReviewable = new RB.DiffReviewable({
            reviewRequest: this.reviewRequest,
            fileIndex: fileIndex,
            fileDiffID: fileDiffID,
            interFileDiffID: interFileDiffID,
            revision: fileDiffRevision,
            interdiffRevision: interdiffRevision,
            serializedCommentBlocks: serializedCommentBlocks
        });

        $.funcQueue('diff_files').add(function() {
            if ($('#file' + fileDiffID).length === 1) {
                /*
                 * We already have this one. This is probably a pre-loaded file.
                 */
                this._renderFileDiff(diffReviewable);
            } else {
                diffReviewable.getRenderedDiff({
                    complete: function(xhr) {
                        $('#file_container_' + fileDiffID)
                            .replaceWith(xhr.responseText);
                        this._renderFileDiff(diffReviewable);
                    }
                }, this);
            }
        }, this);
    },

    /*
     * Sets up a diff as DiffReviewableView and renders it.
     *
     * This will set up a DiffReviewableView for the given diffReviewable.
     * The anchors from this diff render will be stored for navigation.
     *
     * Once rendered and set up, the next diff in the load queue will be
     * pulled from the server.
     */
    _renderFileDiff: function(diffReviewable) {
        var diffReviewableView = new RB.DiffReviewableView({
                el: $('#file' + diffReviewable.get('fileDiffID')),
                model: diffReviewable
            }),
            $anchor;

        this._diffFileIndexView.addDiff(this._diffReviewableViews.length,
                                        diffReviewableView);

        this._diffReviewableViews.push(diffReviewableView);
        diffReviewableView.render();

        this.listenTo(diffReviewableView, 'fileClicked', function() {
            this.selectAnchorByName(diffReviewable.get('fileIndex'));
        });

        this.listenTo(diffReviewableView, 'chunkClicked', function(name) {
            this.selectAnchorByName(name, false);
        });

        /* We must rebuild this every time. */
        this._updateAnchors(diffReviewableView.$el);

        this.listenTo(diffReviewableView, 'chunkExpansionChanged', function() {
            /* The selection rectangle may not update -- bug #1353. */
            this._highlightAnchor($(this._$anchors[this._selectedAnchorIndex]));
        });

        if (this._startAtAnchorName) {
            /* See if we've loaded the anchor the user wants to start at. */
            $anchor = $('a[name="' + this._startAtAnchorName + '"]');

            if ($anchor.length !== 0) {
                this.selectAnchor($anchor);
                this._startAtAnchorName = null;
            }
        }

        $.funcQueue('diff_files').next();
    },

    /*
     * Selects the anchor at a specified location.
     *
     * By default, this will scroll the page to position the anchor near
     * the top of the view.
     */
    selectAnchor: function($anchor, scroll) {
        var i;

        if (!$anchor || $anchor.length === 0 ||
            $anchor.parent().is(':hidden')) {
            return false;
        }

        if (scroll !== false) {
            $(window).scrollTop($anchor.offset().top -
                                this.DIFF_SCROLLDOWN_AMOUNT);
        }

        this._highlightAnchor($anchor);

        for (i = 0; i < this._$anchors.length; i++) {
            if (this._$anchors[i] === $anchor[0]) {
                this._selectedAnchorIndex = i;
                break;
            }
        }

        return true;
    },

    /*
     * Selects an anchor by name.
     */
    selectAnchorByName: function(name, scroll) {
        return this.selectAnchor($('a[name="' + name + '"]'), scroll);
    },

    /*
     * Highlights a chunk bound to an anchor element.
     */
    _highlightAnchor: function($anchor) {
        RB.ChunkHighlighterView.highlight(
            $anchor.parents('tbody:first, thead:first'));
    },

    /*
     * Updates the list of known anchors based on named anchors in the
     * specified table. This is called after every part of the diff that we
     * loaded.
     *
     * If no anchor is selected, we'll try to select the first one.
     */
    _updateAnchors: function($table) {
        this._$anchors = this._$anchors.add($table.find('a[name]'));

        /* Skip over the change index to the first item. */
        if (this._selectedAnchorIndex === -1 && this._$anchors.length > 0) {
            this._selectedAnchorIndex = 0;
            this._highlightAnchor($(this._$anchors[this._selectedAnchorIndex]));
        }
    },

    /*
     * Returns the next navigatable anchor in the specified direction of
     * the given types.
     *
     * This will take a direction to search, starting at the currently
     * selected anchor. The next anchor matching one of the types in the
     * anchorTypes bitmask will be returned. If no anchor is found,
     * null will be returned.
     */
    _getNextAnchor: function(dir, anchorTypes) {
        var $anchor,
            i;

        for (i = this._selectedAnchorIndex + dir;
             i >= 0 && i < this._$anchors.length;
             i += dir) {
            $anchor = $(this._$anchors[i]);

            if (((anchorTypes & this.ANCHOR_COMMENT) &&
                 $anchor.hasClass('comment-anchor')) ||
                ((anchorTypes & this.ANCHOR_FILE) &&
                 $anchor.hasClass('file-anchor')) ||
                ((anchorTypes & this.ANCHOR_CHUNK) &&
                 $anchor.hasClass('chunk-anchor'))) {
                return $anchor;
            }
        }

        return null;
    },

    /*
     * Selects the previous file's header on the page.
     */
    _selectPreviousFile: function() {
        this.selectAnchor(this._getNextAnchor(this.SCROLL_BACKWARD,
                                              this.ANCHOR_FILE));
    },

    /*
     * Selects the next file's header on the page.
     */
    _selectNextFile: function() {
        this.selectAnchor(this._getNextAnchor(this.SCROLL_FORWARD,
                                              this.ANCHOR_FILE));
    },

    /*
     * Selects the previous diff chunk on the page.
     */
    _selectPreviousDiff: function() {
        this.selectAnchor(
            this._getNextAnchor(this.SCROLL_BACKWARD,
                                this.ANCHOR_CHUNK | this.ANCHOR_FILE));
    },

    /*
     * Selects the next diff chunk on the page.
     */
    _selectNextDiff: function() {
        this.selectAnchor(
            this._getNextAnchor(this.SCROLL_FORWARD,
                                this.ANCHOR_CHUNK | this.ANCHOR_FILE));
    },

    /*
     * Selects the previous comment on the page.
     */
    _selectPreviousComment: function() {
        this.selectAnchor(
            this._getNextAnchor(this.SCROLL_BACKWARD, this.ANCHOR_COMMENT));
    },

    /*
     * Selects the next comment on the page.
     */
    _selectNextComment: function() {
        this.selectAnchor(
            this._getNextAnchor(this.SCROLL_FORWARD, this.ANCHOR_COMMENT));
    },

    /*
     * Re-centers the currently selected area on the page.
     */
    _recenterSelected: function() {
        this.selectAnchor($(this._$anchors[this._selectedAnchorIndex]));
    },

    /*
     * Toggles the display of diff chunks that only contain whitespace changes.
     */
    _toggleWhitespaceOnlyChunks: function() {
        _.each(this._diffReviewableViews, function(diffReviewableView) {
            diffReviewableView.toggleWhitespaceOnlyChunks();
        });

        this._$controls.find('.ws').toggle();

        return false;
    },

    /*
     * Toggles the display of extra whitespace highlights on diffs.
     *
     * A cookie will be set to the new whitespace display setting, so that
     * the new option will be the default when viewing diffs.
     */
    _toggleShowExtraWhitespace: function() {
        this._$controls.find('.ew').toggle();
        RB.UserSession.instance.toggleAttr('diffsShowExtraWhitespace');

        return false;
    },

    /*
     * Callback when a revision is selected.
     *
     * Navigates to the selected revision of the diff. If `base` is 0, this
     * will show the single diff revision given in `tip`. Otherwise, this will
     * show an interdiff between `base` and `tip`.
     *
     * TODO: this should show the new revision without reloading the page.
     */
    _onRevisionSelected: function(base, tip) {
        var url = this.reviewRequest.get('reviewURL');

        if (base === 0) {
            url += 'diff/' + tip + '/#index_header';
        } else {
            url += 'diff/' + base + '-' + tip + '/#index_header';
        }

        window.location = url;
    }
});
_.extend(RB.DiffViewerPageView.prototype, RB.KeyBindingsMixin);


})();
