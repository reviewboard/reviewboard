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

    events: {
        'click .index a': '_onIndexClicked',
        'click .toggle-whitespace-only-chunks': '_toggleWhitespaceOnlyChunks',
        'click .toggle-show-whitespace': '_toggleShowExtraWhitespace'
    },

    /*
     * Initializes the diff viewer page.
     */
    initialize: function() {
        var url;

        _.super(this).initialize.call(this);

        this._selectedAnchorIndex = -1;
        this._$anchors = $();
        this._$controls = null;
        this._$indexes = null;
        this._diffReviewableViews = [];

        /* Check to see if there's an anchor we need to scroll to. */
        url = document.location.toString();
        this._startAtAnchorName = (url.match('#') ? url.split('#')[1] : null);
    },

    /*
     * Renders the page and begins loading all diffs.
     */
    render: function() {
        var $reviewRequest;

        _.super(this).render.call(this);

        $reviewRequest = this.$('.review-request');

        this._$controls = $reviewRequest.find('ul.controls');
        this._$indexes = $reviewRequest.find('ol.index');

        $('#diffs').bindClass(RB.UserSession.instance,
                              'diffsShowExtraWhitespace', 'ewhl');

        $.funcQueue("diff_files").start();

        return this;
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
        var fileDiffID = diffReviewable.get('fileDiffID'),
            tableID = 'file' + fileDiffID,
            $table = $('#' + tableID),
            diffReviewableView = new RB.DiffReviewableView({
                el: $table,
                model: diffReviewable
            }),
            $anchor;

        this._diffReviewableViews.push(diffReviewableView);
        diffReviewableView.render();

        this.listenTo(diffReviewableView, 'chunkDimmed chunkUndimmed',
                      function(chunkID) {
            this._$indexes.find('a[href="#' + chunkID + '"]')
                .toggleClass('dimmed');
        });

        this.listenTo(diffReviewableView, 'fileClicked', function() {
            this.selectAnchorByName(diffReviewable.get('fileIndex'));
        });

        this.listenTo(diffReviewableView, 'chunkClicked', function(name) {
            this.selectAnchorByName(name, false);
        });

        /* We must rebuild this every time. */
        this._updateAnchors($table);

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
     * Handler for when a file/chunk index is clicked.
     *
     * Navigates to the proper file or chunk header for this anchor.
     */
    _onIndexClicked: function(e) {
        this.selectAnchorByName(e.target.href.split('#')[1]);

        return false;
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
    }
});
_.extend(RB.DiffViewerPageView.prototype, RB.KeyBindingsMixin);
