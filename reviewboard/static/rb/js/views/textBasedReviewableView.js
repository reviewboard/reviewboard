/*
 * Base for text-based review UIs.
 *
 * This will display all existing comments on an element by displaying a comment
 * indicator beside it. Users can place a comment by clicking on a line, which
 * will get a light-grey background color upon mouseover, and placing a comment
 * in the comment dialog that is displayed.
 */
RB.TextBasedReviewableView = RB.FileAttachmentReviewableView.extend({
    commentBlockView: RB.TextBasedCommentBlockView,

    /*
     * Initializes the view.
     */
    initialize: function(options) {
        RB.FileAttachmentReviewableView.prototype.initialize.call(
            this, options);

        this._$viewTabs = null;
        this._$textTable = null;
        this._$renderedTable = null;
        this._textSelector = null;
        this._renderedSelector = null;

        this.on('commentBlockViewAdded', this._placeCommentBlockView, this);

        this.router = new Backbone.Router({
            routes: {
                ':viewMode(/line:lineNum)': 'viewMode'
            }
        });
        this.listenTo(
            this.router, 'route:viewMode',
            function(viewMode, lineNum) {
                /*
                 * Router's pattern matching isn't very good. Since we don't
                 * want to stick "view" or something before the view mode,
                 * and we want to allow for view, line, or view + line, we need
                 * to check and transform viewMode if it seems to be a line
                 * reference.
                 */
                if (viewMode.indexOf('line') === 0) {
                    lineNum = viewMode.substr(4);
                    viewMode = null;
                }

                if (viewMode) {
                    this.model.set('viewMode', viewMode);
                }

                if (lineNum) {
                    this._scrollToLine(lineNum);
                }
            });
    },

    /*
     * Removes the reviewable from the DOM.
     */
    remove: function() {
        _super(this).remove.call(this);

        this._textSelector.remove();
        this._renderedSelector.remove();
    },

    /*
     * Renders the view.
     */
    renderContent: function() {
        var $fileHeader;

        this._$viewTabs = this.$('.text-review-ui-views li');

        /* Set up the source text table. */
        this._$textTable = this.$('.text-review-ui-text-table');

        this._textSelector = new RB.TextCommentRowSelector({
            el: this._$textTable,
            reviewableView: this
        });
        this._textSelector.render();

        if (this.model.get('hasRenderedView')) {
            /* Set up the rendered table. */
            this._$renderedTable = this.$('.text-review-ui-rendered-table');

            this._renderedSelector = new RB.TextCommentRowSelector({
                el: this._$renderedTable,
                reviewableView: this
            });
            this._renderedSelector.render();
        }

        this.listenTo(this.model, 'change:viewMode', this._onViewChanged);

        $fileHeader = this.$('.review-ui-header');

        if (this.model.get('numRevisions') > 1) {
            this._revisionSelectorView = new RB.FileAttachmentRevisionSelectorView({
                el: $fileHeader.find('#attachment_revision_selector'),
                model: this.model
            });
            this._revisionSelectorView.render();
            this.listenTo(this._revisionSelectorView, 'revisionSelected',
                          this._onRevisionSelected);

            this._revisionLabelView = new RB.FileAttachmentRevisionLabelView({
                el: $fileHeader.find('#revision_label'),
                model: this.model
            });
            this._revisionLabelView.render();
            this.listenTo(this._revisionLabelView, 'revisionSelected',
                          this._onRevisionSelected);
        }

        Backbone.history.start({
            root: window.location
        });
    },

    /*
     * Callback for when a new file revision is selected.
     *
     * This supports single revisions and diffs. If `base is 0, a
     * single revision is selected, If not, the diff between `base` and
     * `tip` will be shown.
     */
    _onRevisionSelected: function(revisions) {
        var revisionIDs = this.model.get('attachmentRevisionIDs'),
            base = revisions[0],
            tip = revisions[1],
            revisionBase,
            revisionTip,
            redirectURL;

        // Ignore clicks on No Diff Label
        if (tip === 0) {
            return;
        }

        revisionTip = revisionIDs[tip-1];

        /* Eventually these hard redirects will use a router
         * (see diffViewerPageView.js for example)
         * this.router.navigate(base + '-' + tip + '/', {trigger: true});
         */

        if (base === 0) {
            redirectURL = '../' + revisionTip + '/';
        } else {
            revisionBase = revisionIDs[base-1];
            redirectURL = '../' + revisionBase + '-' + revisionTip + '/';
        }
        window.location.replace(redirectURL);
    },

    /*
     * Scrolls the page to the top of the specified line number.
     */
    _scrollToLine: function(lineNum) {
        var $table = this._getTableForViewMode(this.model.get('viewMode')),
            rows = $table[0].tBodies[0].rows,
            $row;

        /* Normalize this to a valid row index. */
        lineNum = RB.MathUtils.clip(lineNum, 1, rows.length) - 1;

        $row = $($table[0].tBodies[0].rows[lineNum]);
        $(window).scrollTop($row.offset().top);
    },

    /*
     * Returns the table element for the given view mode.
     */
    _getTableForViewMode: function(viewMode) {
        if (viewMode === 'source') {
            return this._$textTable;
        } else if (viewMode === 'rendered' &&
                   this.model.get('hasRenderedView')) {
            return this._$renderedTable;
        } else {
            console.assert(false, 'Unexpected viewMode ' + viewMode);
            return null;
        }
    },

    /*
     * Returns the row selector for the given view mode.
     */
    _getRowSelectorForViewMode: function(viewMode) {
        if (viewMode === 'source') {
            return this._textSelector;
        } else if (viewMode === 'rendered' &&
                   this.model.get('hasRenderedView')) {
            return this._renderedSelector;
        } else {
            console.assert(false, 'Unexpected viewMode ' + viewMode);
            return null;
        }
    },

    /*
     * Adds the comment view to the line the comment was created on.
     */
    _placeCommentBlockView: function(commentBlockView) {
        var commentBlock = commentBlockView.model,
            beginLineNum = commentBlock.get('beginLineNum'),
            endLineNum = commentBlock.get('endLineNum'),
            rowSelector,
            viewMode,
            rowEls,
            rows;

        if (beginLineNum && endLineNum) {
            viewMode = commentBlock.get('viewMode');
            rowSelector = this._getRowSelectorForViewMode(viewMode);

            if (!rowSelector) {
                return;
            }

            if (this.model.get('diffRevision')) {
                /*
                 * We're showing a diff, so we need to do a search for the
                 * rows matching the given line numbers.
                 */
                rowEls = rowSelector.getRowsForRange(beginLineNum, endLineNum);
            } else {
                /*
                 * Since we know we have the entire content of the text in one
                 * list, we don't need to use getRowsForRange here, and instead
                 * can look up the lines directly in the lists of rows.
                 */
                rows = rowSelector.el.tBodies[0].rows;

                /* The line numbers are 1-based, so normalize for the rows. */
                rowEls = [rows[beginLineNum - 1], rows[endLineNum - 1]];
            }

            if (rowEls) {
                commentBlockView.setRows($(rowEls[0]), $(rowEls[1]));
                commentBlockView.$el.appendTo(
                    commentBlockView.$beginRow[0].cells[0]);
            }
        }
    },

    /*
     * Handler for when the view changes.
     *
     * This will set the correct tab to be active and switch which table of
     * text is shown.
     */
    _onViewChanged: function() {
        var viewMode = this.model.get('viewMode');

        this._$viewTabs
            .removeClass('active')
            .filter('[data-view-mode=' + viewMode + ']')
                .addClass('active');

        this._$textTable.setVisible(viewMode === 'source');
        this._$renderedTable.setVisible(viewMode === 'rendered');

        /* Cause all comments to recalculate their sizes. */
        $(window).triggerHandler('resize');
    }
});
