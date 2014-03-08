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

        Backbone.history.start({
            root: window.location
        });
    },

    /*
     * Scrolls the page to the top of the specified line number.
     */
    _scrollToLine: function(lineNum) {
        var $table = this._getTableForViewMode(this.model.get('viewMode')),
            rows = $table[0].tBodies[0].rows,
            $row;

        /* Normalize this to a valid row index. */
        lineNum--;
        lineNum = Math.max(0, Math.min(lineNum, rows.length - 1));

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
     * Adds the comment view to the line the comment was created on.
     */
    _placeCommentBlockView: function(commentBlockView) {
        var commentBlock = commentBlockView.model,
            beginLineNum = commentBlock.get('beginLineNum'),
            endLineNum = commentBlock.get('endLineNum'),
            $table,
            viewMode,
            rows;

        if (beginLineNum && endLineNum) {
            viewMode = commentBlock.get('viewMode');
            $table = this._getTableForViewMode(viewMode);

            if ($table !== null) {
                rows = $table[0].tBodies[0].rows;

                /* The line numbers are 1-based, so normalize for the rows. */
                commentBlockView.setRows($(rows[beginLineNum - 1]),
                                         $(rows[endLineNum - 1]));
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
