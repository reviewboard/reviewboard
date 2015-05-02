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

    DIFF_SCROLLDOWN_AMOUNT: 15,

    keyBindings: {
        'aAKP<m': '_selectPreviousFile',
        'fFJN>': '_selectNextFile',
        'sSkp,': '_selectPreviousDiff',
        'dDjn.': '_selectNextDiff',
        '[x': '_selectPreviousComment',
        ']c': '_selectNextComment',
        '\x0d': '_recenterSelected',
        'rR': '_createComment'
    },

    events: _.extend({
        'click .toggle-whitespace-only-chunks': '_toggleWhitespaceOnlyChunks',
        'click .toggle-show-whitespace': '_toggleShowExtraWhitespace'
    }, RB.ReviewablePageView.prototype.events),

    /*
     * Initializes the diff viewer page.
     */
    initialize: function() {
        var revisionInfo = this.model.get('revision'),
            curRevision = revisionInfo.get('revision'),
            curInterdiffRevision = revisionInfo.get('interdiffRevision'),
            url = document.location.toString(),
            hash = document.location.hash || '',
            search = document.location.search || '',
            revisionRange;

        _super(this).initialize.call(this);

        this._selectedAnchorIndex = -1;
        this._$anchors = $();
        this._$controls = null;
        this._diffReviewableViews = [];
        this._diffFileIndexView = null;
        this._highlightedChunk = null;

        this.listenTo(this.model.get('files'), 'update', this._setFiles);

        /* Check to see if there's an anchor we need to scroll to. */
        this._startAtAnchorName = (url.match('#') ? url.split('#')[1] : null);

        this.router = new Backbone.Router({
            routes: {
                ':revision/': 'revision',
                ':revision/?page=:page': 'revision'
            }
        });
        this.listenTo(this.router, 'route:revision', function(revision, page) {
            var parts;

            if (page === undefined) {
                page = 1;
            } else {
                page = parseInt(page, 10);
            }

            if (revision.indexOf('-') === -1) {
                this._loadRevision(0, parseInt(revision, 10), page);
            } else {
                parts = revision.split('-', 2);
                this._loadRevision(parseInt(parts[0], 10),
                                   parseInt(parts[1], 10),
                                   page);
            }
        });

        /*
         * Begin managing the URL history for the page, so that we can
         * switch revisions and handle pagination while keeping the history
         * clean and the URLs representative of the current state.
         *
         * Note that Backbone will attempt to convert the hash to part of
         * the page URL, stripping away the "#". This will result in a
         * URL pointing to an incorrect, possible non-existent diff revision.
         *
         * We work around that by saving the values for the hash and query
         * string (up above), and by later replacing the current URL with a
         * new one that, amongst other things, contains the hash present
         * when the page was loaded.
         */
        Backbone.history.start({
            pushState: true,
            hashChange: false,
            root: this.options.reviewRequestData.reviewURL + 'diff/',
            silent: true
        });

        /*
         * Navigating here accomplishes two things:
         *
         * 1. The user may have viewed diff/, and not diff/<revision>/, but
         *    we want to always show the revision in the URL. This ensures
         *    we have a URL equivalent to the one we get when clicking
         *    a revision in the slider.
         *
         * 2. We want to add back any hash and query string that was
         *    stripped away.
         *
         * We won't be invoking any routes or storing new history. The back
         * button will correctly bring the user to the previous page.
         */
        revisionRange = curRevision;

        if (curInterdiffRevision) {
            revisionRange += '-' + curInterdiffRevision;
        }

        this.router.navigate(revisionRange + '/' + search + hash, {
            replace: true,
            trigger: false
        });
    },

    /*
     * Removes the view from the page.
     */
    remove: function() {
        _super(this).remove.call(this);

        this._diffFileIndexView.remove();
    },

    /*
     * Renders the page and begins loading all diffs.
     */
    render: function() {
        var $reviewRequest,
            numDiffs = this.model.get('numDiffs'),
            revisionModel = this.model.get('revision');

        _super(this).render.call(this);

        $reviewRequest = this.$('.review-request');

        this._$controls = $reviewRequest.find('ul.controls');

        this._diffFileIndexView = new RB.DiffFileIndexView({
            el: $('#diff_index'),
            collection: this.model.get('files')
        });
        this._diffFileIndexView.render();

        this.listenTo(this._diffFileIndexView, 'anchorClicked',
                      this.selectAnchorByName);

        this._diffRevisionLabelView = new RB.DiffRevisionLabelView({
            el: $('#diff_revision_label'),
            model: revisionModel
        });
        this._diffRevisionLabelView.render();

        this.listenTo(this._diffRevisionLabelView, 'revisionSelected',
                      this._onRevisionSelected);

        if (numDiffs > 1) {
            this._diffRevisionSelectorView = new RB.DiffRevisionSelectorView({
                el: $('#diff_revision_selector'),
                model: revisionModel,
                numDiffs: numDiffs
            });
            this._diffRevisionSelectorView.render();

            this.listenTo(this._diffRevisionSelectorView, 'revisionSelected',
                          this._onRevisionSelected);
        }

        this._commentsHintModel = this.options.commentsHint;
        this._commentsHintView = new RB.DiffCommentsHintView({
            el: $('#diff_comments_hint'),
            model: this.model.get('commentsHint')
        });
        this._commentsHintView.render();
        this.listenTo(this._commentsHintView, 'revisionSelected',
                      this._onRevisionSelected);

        this._paginationView1 = new RB.PaginationView({
            el: $('#pagination1'),
            model: this.model.get('pagination')
        });
        this._paginationView1.render();
        this.listenTo(this._paginationView1, 'pageSelected',
                      _.partial(this._onPageSelected, false));

        this._paginationView2 = new RB.PaginationView({
            el: $('#pagination2'),
            model: this.model.get('pagination')
        });
        this._paginationView2.render();
        this.listenTo(this._paginationView2, 'pageSelected',
                      _.partial(this._onPageSelected, true));

        $('#diffs').bindClass(RB.UserSession.instance,
                              'diffsShowExtraWhitespace', 'ewhl');

        this._setFiles();

        $('#diff-details').removeClass('loading');

        return this;
    },

    _fileEntryTemplate: _.template([
        '<div class="diff-container">',
        ' <div class="diff-box">',
        '  <table class="sidebyside loading <% if (newfile) { %>newfile<% } %>"',
        '         id="file_container_<%- id %>">',
        '   <thead>',
        '    <tr class="filename-row">',
        '     <th><%- depotFilename %></th>',
        '    </tr>',
        '   </thead>',
        '   <tbody>',
        '    <tr><td><pre>&nbsp;</pre></td></tr>',
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
     */
    _setFiles: function() {
        var files = this.model.get('files'),
            $diffs = $('#diffs').empty();

        this._highlightedChunk = null;

        files.each(function(file) {
            var filediff = file.get('filediff'),
                interfilediff = file.get('interfilediff'),
                interdiffRevision = null;

            $diffs.append(this._fileEntryTemplate(file.attributes));

            if (interfilediff) {
                interdiffRevision = interfilediff.revision;
            } else if (file.get('forceInterdiff')) {
                interdiffRevision = file.get('forceInterdiffRevision');
            }

            this.queueLoadDiff(filediff.id,
                               filediff.revision,
                               interfilediff ? interfilediff.id : null,
                               interdiffRevision,
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
        var $el = $('#file' + diffReviewable.get('fileDiffID')),
            diffReviewableView,
            $anchor;

        if ($el.length === 0) {
            /*
             * The user changed revsions before the file finished loading, and
             * the target element no longer exists. Just return.
             */
            $.funcQueue('diff_files').next();
            return;
        }

        diffReviewableView = new RB.DiffReviewableView({
            el: $el,
            model: diffReviewable
        });

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

        this.listenTo(diffReviewableView, 'moveFlagClicked', function(line) {
            this.selectAnchor(this.$('a[target=' + line + ']'));
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
        var scrollAmount,
            i,
            url;

        if (!$anchor || $anchor.length === 0 ||
            $anchor.parent().is(':hidden')) {
            return false;
        }

        if (scroll !== false) {
            url = [
                this._getCurrentURL(),
                location.search,
                '#',
                $anchor.attr('name')
            ].join('');

            this.router.navigate(url, {
                replace: true,
                trigger: false
            });

            scrollAmount = this.DIFF_SCROLLDOWN_AMOUNT;

            if (RB.DraftReviewBannerView.instance) {
                scrollAmount += RB.DraftReviewBannerView.instance.getHeight();
            }

            $(window).scrollTop($anchor.offset().top - scrollAmount);
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
        this._highlightedChunk = $anchor.parents('tbody:first, thead:first');
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

            if ($anchor.parents('tr').hasClass('dimmed')) {
                continue;
            }

            if (((anchorTypes & this.ANCHOR_COMMENT) &&
                 $anchor.hasClass('commentflag-anchor')) ||
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
    * Creates a comment for a chunk of a diff
    */
    _createComment: function() {
        var chunkID = this._highlightedChunk[0].id,
            chunkElement = document.getElementById(chunkID),
            lineElements,
            beginLineNum,
            beginNode,
            endLineNum,
            endNode;

        if (chunkElement) {
            lineElements = chunkElement.getElementsByTagName('tr');
            beginLineNum = lineElements[0].getAttribute("line");
            beginNode = lineElements[0].cells[2];
            endLineNum = lineElements[lineElements.length-1]
                .getAttribute("line");
            endNode = lineElements[lineElements.length-1].cells[2];

            _.each(this._diffReviewableViews, function(diffReviewableView) {
                if ($.contains(diffReviewableView.el, beginNode)){
                    diffReviewableView.createComment(beginLineNum, endLineNum,
                                                     beginNode, endNode);
                }
            });
        }
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
     * Callback for when a new revision is selected.
     *
     * This supports both single revisions and interdiffs. If `base` is 0, a
     * single revision is selected. If not, the interdiff between `base` and
     * `tip` will be shown.
     *
     * This will always implicitly navigate to page 1 of any paginated diffs.
     */
    _onRevisionSelected: function(base, tip) {
        if (base === 0) {
            this.router.navigate(tip + '/', {trigger: true});
        } else {
            this.router.navigate(base + '-' + tip + '/', {trigger: true});
        }
    },

    /*
     * Get the current URL.
     *
     * This will compute and return the current page's URL (relative to the
     * router root), not including query parameters or hash locations.
     */
    _getCurrentURL: function() {
        var revision = this.model.get('revision'),
            url = revision.get('revision');

        if (revision.get('interdiffRevision') !== null) {
            url += '-' + revision.get('interdiffRevision');
        }

        return url;
    },

    /*
     * Callback for when a new page is selected.
     *
     * Navigates to the same revision with a different page number.
     */
    _onPageSelected: function(scroll, page) {
        var url = this._getCurrentURL();

        if (scroll) {
            this.selectAnchorByName('index_header', true);
        }

        url += '/?page=' + page;
        this.router.navigate(url, {trigger: true});
    },

    /*
     * Load a given revision.
     *
     * This supports both single revisions and interdiffs. If `base` is 0, a
     * single revision is selected. If not, the interdiff between `base` and
     * `tip` will be shown.
     */
    _loadRevision: function(base, tip, page) {
        var reviewRequestURL = _.result(this.reviewRequest, 'url'),
            contextURL = reviewRequestURL + 'diff-context/',
            $downloadLink = $('#download-diff');

        if (base === 0) {
            contextURL += '?revision=' + tip;
            $downloadLink.show();
        } else {
            contextURL += '?revision=' + base + '&interdiff-revision=' + tip;
            $downloadLink.hide();
        }

        if (page !== 1) {
            contextURL += '&page=' + page;
        }

        $.ajax(contextURL).done(_.bind(function(rsp) {
            _.each(this._diffReviewableViews, function(diffReviewableView) {
                diffReviewableView.remove();
            });
            this._diffReviewableViews = [];

            this.model.set(this.model.parse(rsp.diff_context));
        }, this));
    }
});
_.extend(RB.DiffViewerPageView.prototype, RB.KeyBindingsMixin);
