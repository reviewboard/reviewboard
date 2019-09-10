/**
 * Base for text-based review UIs.
 *
 * This will display all existing comments on an element by displaying a comment
 * indicator beside it. Users can place a comment by clicking on a line, which
 * will get a light-grey background color upon mouseover, and placing a comment
 * in the comment dialog that is displayed.
 */
RB.TextBasedReviewableView = RB.FileAttachmentReviewableView.extend({
    commentBlockView: RB.TextBasedCommentBlockView,

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     */
    initialize(options) {
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
                ':viewMode(/line:lineNum)': 'viewMode',
            },
        });
        this.listenTo(this.router, 'route:viewMode', (viewMode, lineNum) => {
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

    /**
     * Remove the reviewable from the DOM.
     */
    remove() {
        _super(this).remove.call(this);

        this._textSelector.remove();
        this._renderedSelector.remove();
    },

    /**
     * Render the view.
     */
    renderContent() {
        this._$viewTabs = this.$('.text-review-ui-views li');

        // Set up the source text table.
        this._$textTable = this.$('.text-review-ui-text-table');

        this._textSelector = new RB.TextCommentRowSelector({
            el: this._$textTable,
            reviewableView: this
        });
        this._textSelector.render();

        if (this.model.get('hasRenderedView')) {
            // Set up the rendered table.
            this._$renderedTable = this.$('.text-review-ui-rendered-table');

            this._renderedSelector = new RB.TextCommentRowSelector({
                el: this._$renderedTable,
                reviewableView: this
            });
            this._renderedSelector.render();
        }

        this.listenTo(this.model, 'change:viewMode', this._onViewChanged);

        const $fileHeader = this.$('.review-ui-header');

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

        const reviewURL = this.model.get('reviewRequest').get('reviewURL');
        const attachmentID = this.model.get('fileAttachmentID');
        Backbone.history.start({
            root: `${reviewURL}file/${attachmentID}/`,
        });
    },

    /**
     * Callback for when a new file revision is selected.
     *
     * This supports single revisions and diffs. If ``base`` is 0, a
     * single revision is selected, If not, the diff between ``base`` and
     * ``tip`` will be shown.
     *
     * Args:
     *     revisions (array of number):
     *         A 2-element array containing the new revisions to be viewed.
     */
    _onRevisionSelected(revisions) {
        const [base, tip] = revisions;

        // Ignore clicks on No Diff Label.
        if (tip === 0) {
            return;
        }

        const revisionIDs = this.model.get('attachmentRevisionIDs');
        const revisionTip = revisionIDs[tip - 1];

        /*
         * Eventually these hard redirects will use a router
         * (see diffViewerPageView.js for example)
         * this.router.navigate(base + '-' + tip + '/', {trigger: true});
         */
        let redirectURL;

        if (base === 0) {
            redirectURL = `../${revisionTip}/`;
        } else {
            const revisionBase = revisionIDs[base - 1];
            redirectURL = `../${revisionBase}-${revisionTip}/`;
        }

        window.location.replace(redirectURL);
    },

    /**
     * Scroll the page to the top of the specified line number.
     *
     * Args:
     *     lineNum (number):
     *         The line number to scroll to.
     */
    _scrollToLine(lineNum) {
        const $table = this._getTableForViewMode(this.model.get('viewMode'));
        const rows = $table[0].tBodies[0].rows;

        /* Normalize this to a valid row index. */
        lineNum = RB.MathUtils.clip(lineNum, 1, rows.length) - 1;

        const $row = $($table[0].tBodies[0].rows[lineNum]);
        $(window).scrollTop($row.offset().top);
    },

    /**
     * Return the table element for the given view mode.
     *
     * Args:
     *     viewMode (string):
     *         The view mode to show.
     *
     * Returns:
     *     jQuery:
     *     The table element corresponding to the requested view mode.
     */
    _getTableForViewMode(viewMode) {
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

    /**
     * Return the row selector for the given view mode.
     *
     * Args:
     *     viewMode (string):
     *         The view mode to show.
     *
     * Returns:
     *     RB.TextCommentRowSelector:
     *     The row selector.
     */
    _getRowSelectorForViewMode(viewMode) {
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

    /**
     * Add the comment view to the line the comment was created on.
     *
     * Args:
     *     commentBlockView (RB.AbstractCommentBlockView):
     *         The comment view to add.
     */
    _placeCommentBlockView(commentBlockView) {
        const commentBlock = commentBlockView.model;
        const beginLineNum = commentBlock.get('beginLineNum');
        const endLineNum = commentBlock.get('endLineNum');

        if (beginLineNum && endLineNum) {
            const viewMode = commentBlock.get('viewMode');
            const rowSelector = this._getRowSelectorForViewMode(viewMode);

            if (!rowSelector) {
                return;
            }

            let rowEls;

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
                const rows = rowSelector.el.tBodies[0].rows;

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

    /**
     * Handle a change to the view mode.
     *
     * This will set the correct tab to be active and switch which table of
     * text is shown.
     */
    _onViewChanged() {
        const viewMode = this.model.get('viewMode');

        this._$viewTabs
            .removeClass('active')
            .filter(`[data-view-mode=${viewMode}]`)
                .addClass('active');

        this._$textTable.setVisible(viewMode === 'source');
        this._$renderedTable.setVisible(viewMode === 'rendered');

        /* Cause all comments to recalculate their sizes. */
        $(window).triggerHandler('resize');
    },
});
